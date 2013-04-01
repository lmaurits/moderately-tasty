import collections
import functools
import sqlite3
import urlparse
import time

import requests
from BeautifulSoup import BeautifulSoup

import config

class Link():
    
    def __init__(self, title="Untitled", url=None):
        self.id = None
        self.title = title
        self.url = url
        self.created = None
        self.tags = []

    def datetime(self):
        "Return a string containing the nicely formatted time a link was first svaed."
        return time.strftime("%d %b %Y", time.gmtime(self.created))

    def domain(self):
        "Return a string containing the domain of a link's URL."
        return urlparse.urlparse(self.url).netloc

    def prettytitle(self):
        "Return a nice-looking string to act as a link's title."
        if self.title:
            return self.title
        else:
            return "Untitled (%s)" % self.url

def db_access(f):
    "A function wrapper which opens/closes the SQLite database as necessary."
    # Why  not just set up self.con and self.cur once at instantiation and
    # leave it at that?  Because connections/cursors can only be used from
    # the thread they are created in, and each HTTP request gets its own
    # thread, so we need to open/close the DB connection each time...
    @functools.wraps(f)
    def decorated(self, *args, **kwargs):
        already_open = self.db_open
        if not self.db_open:
            self.con = sqlite3.connect("modtasty.db")
            self.cur = self.con.cursor()
            self.db_open = True
        retval = f(self, *args, **kwargs)
        if not already_open:
            self.cur.close()
            self.con.commit()
            self.con.close()
            self.db_open = False
        return retval
    return decorated

class ModTasty():

    def __init__(self):

        self.con = None
        self.cur = None
        self.db_open = False
        # Store some configuration options
        self.username = config.username
        self.password = config.password
        self.email_errors = config.email_errors
        self.admin_email = config.admin_email
        # Set up database
        self.initialise_db()

    def check_auth(self, username, password):
        "Check that provided credentials match those in the config file."
        return username == self.username and password == self.password

    @db_access
    def initialise_db(self):
        "Create database tables if they don't already exist."

        self.cur.execute("""CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY ASC,
                title TEXT,
                url TEXT,
                created INTEGER
                )""")

        self.cur.execute("""CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY ASC,
                name TEXT
                )""")

        self.cur.execute("""CREATE TABLE IF NOT EXISTS link_tag_connections (
                link_id INTEGER,
                tag_id INTEGER,
                FOREIGN KEY(link_id) REFERENCES links(id),
                FOREIGN KEY(tag_id) REFERENCES tags(id)
                )""")


    def make_link_from_table_row(self, row):
        "Build a Link object from a list returned from a database cursor fetch method."

        link = Link()
        link.id = row[0]
        link.title = row[1]
        link.url = row[2]
        link.created = row[3]
        return link

    def make_link_from_url(self, url):
        "Use a URL to instantiate a Link object, setting the url and title fields."

        link = Link(url=url)
        r = requests.get(url)
        s = BeautifulSoup(r.text)
        link.title = s.title.string
        return link

    @db_access
    def save_link(self, link):
        "Save a Link object to the database, via INSERT or UPDATE as necessary"

        if not link.created:
            link.created = time.time()
        if link.id:
            self.cur.execute("""UPDATE links SET title=?, url=? WHERE id=?""", (link.title, link.url, link.id))
        else:
            self.cur.execute("""INSERT INTO links (title, url, created) VALUES (?, ?, ?)""", (link.title, link.url, link.created))
            self.cur.execute("""SELECT id FROM links WHERE url=?""", (link.url,))
            link.id = self.cur.fetchone()[0]

        self.cur.execute("""DELETE from link_tag_connections WHERE link_id=?""", (link.id,))
        for tag in link.tags:
            self.cur.execute("""SELECT id FROM tags WHERE name=?""", (tag,))
            tag_id = self.cur.fetchall()
            if tag_id:
                tag_id = tag_id[0][0]
                self.cur.execute("""INSERT INTO link_tag_connections VALUES (?, ?)""", (link.id, tag_id))
            else:
                self.cur.execute("""INSERT INTO tags (name) VALUES (?)""", (tag, ))
                self.cur.execute("""SELECT id FROM tags WHERE name=?""", (tag, ))
                tag_id = self.cur.fetchone()[0]
                self.cur.execute("""SELECT id FROM tags WHERE name=?""", (tag, ))
                self.cur.execute("""INSERT INTO link_tag_connections VALUES (?, ?)""", (link.id, tag_id))

    @db_access
    def get_link_by_id(self, id):
        "Return a Link object corresponding to an id in the database link table."
        
        self.cur.execute("""SELECT * FROM links WHERE id=?""", (id, ))
        link = self.make_link_from_table_row(self.cur.fetchone())
        self.cur.execute("""SELECT tag_id FROM link_tag_connections WHERE link_id=?""", (id, ))
        for tag_id in self.cur.fetchall():
            tag_id = tag_id[0]
            self.cur.execute("""SELECT name FROM tags WHERE id=?""", (tag_id, ))
            link.tags.append(self.cur.fetchone()[0])
            link.tags.sort()
        return link

    @db_access
    def delete_link_by_id(self, id):
        "Delete the link with the given id from the database."
        self.cur.execute("""DELETE FROM links WHERE id=?""", (id, ))
        self.cur.execute("""SELECT tag_id FROM link_tag_connections WHERE link_id=?""", (id, ))
        tag_ids = self.cur.fetchall()
        self.cur.execute("""DELETE FROM link_tag_connections WHERE link_id=?""", (id, ))
        # Delete any tags for which this link was the last link tagged as such
        for tag_id in tag_ids:
            self.cur.execute("""SELECT COUNT(tag_id) FROM link_tag_connections WHERE tag_id=?""", (tag_id[0], ))
            count = self.cur.fetchone()[0]
            if count is 0:
                self.cur.execute("""DELETE FROM tags WHERE id=?""", (tag_id[0], ))

    @db_access
    def get_latest_links(self):
        "Return a list of the most recently created Link objects."
        self.cur.execute("""SELECT id FROM links ORDER BY created DESC LIMIT 20""")
        links = [self.get_link_by_id(id[0]) for id in self.cur.fetchall()]
        return links

    @db_access
    def get_all_tags_and_counts(self):
        "Return a list of all tags in the database, and a list of the number of links with each tag."
        self.cur.execute("""SELECT tags.name, COUNT(tags.id)  FROM tags INNER JOIN link_tag_connections ON tags.id = link_tag_connections.tag_id GROUP BY tags.id ORDER BY COUNT(tags.id) DESC""")
        tc = self.cur.fetchall()
        tags = [t[0] for t in tc]
        counts = [t[1] for t in tc]
        return tags, counts
       
    @db_access
    def get_links_by_tag_name(self, tag_name):
        "Return a list of all Link objects which have the specified tag"

        self.cur.execute("""SELECT id FROM tags WHERE name=?""", (tag_name,))
        tag_id = self.cur.fetchall()
        if not tag_id:
            return []
        self.cur.execute("""SELECT links.id FROM links INNER JOIN link_tag_connections ON links.id = link_tag_connections.link_id WHERE link_tag_connections.tag_id=? ORDER BY links.created DESC""", (tag_id[0][0],))
        links = [self.get_link_by_id(id[0]) for id in self.cur.fetchall()]
        return links
