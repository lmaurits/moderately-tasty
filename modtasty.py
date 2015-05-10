import functools
import sqlite3
import urllib2
import urlparse
import time

from BeautifulSoup import BeautifulSoup

class Link():
    
    def __init__(self, id=None, title="Untitled", url=None, created=None, tags=None):
        self.id = id
        self.title = title
        self.url = url
        self.created = created
        if tags:
            self.tags = tags
        else:
            self.tags = []

    def datetime(self):
        "Return a string containing the nicely formatted time a link was first svaed."
        return time.strftime("%d %b %Y", time.gmtime(self.created))

    def domain(self):
        "Return a string containing the domain of a link's URL."
        return urlparse.urlparse(self.url).netloc

    def prettytitle(self):
        "Return a nice-looking string to act as a link's title."
        return self.title or ("Untitled (%s)" % self.url)

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

        self.con, self.cur, self.db_open = None, None, False
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


    def make_link_from_url(self, url):
        "Use a URL to instantiate a Link object, setting the url and title fields."
        link = Link(url=url)
        u = urllib2.urlopen(url)
        s = BeautifulSoup(u.read())
        link.title = s.title.string if s.title else "Untitled"
        return link

    @db_access
    def save_link(self, link):
        "Save a Link object to the database, via INSERT or UPDATE as necessary"
        old = True
        if link.id:
            # Updating an existing link
            old_tags = self.get_link_by_id(link.id).tags
            self.cur.execute("""UPDATE links SET title=?, url=? WHERE id=?""", (link.title, link.url, link.id))
        else:
            # Creating a new link
            old = False
            link.created = time.time()
            self.cur.execute("""INSERT INTO links (title, url, created) VALUES (?, ?, ?)""", (link.title, link.url, link.created))
            link.id = self.cur.lastrowid
        self.cur.execute("""DELETE from link_tag_connections WHERE link_id=?""", (link.id,))
        # Save new tags
        for tag in link.tags:
            self.cur.execute("""SELECT id FROM tags WHERE name=?""", (tag,))
            tag_id = self.cur.fetchone()
            if not tag_id:
                self.cur.execute("""INSERT INTO tags (name) VALUES (?)""", (tag, ))
                tag_id = (self.cur.lastrowid,)
            self.cur.execute("""INSERT INTO link_tag_connections VALUES (?, ?)""", (link.id, tag_id[0]))
        # Kill removed tags if they're no longer used by any link
        if old:
            for tag in old_tags:
                if tag not in link.tags:
                    self.cur.execute("""SELECT id FROM tags WHERE name=?""", (tag,))
                    self.kill_unused_tag(self.cur.fetchone()[0])

    @db_access
    def get_link_by_id(self, id):
        "Return a Link object corresponding to an id in the database link table."
        self.cur.execute("""SELECT * FROM links WHERE id=?""", (id, ))
        row = self.cur.fetchone()
        if not row:
                return None
        link = Link(*row)
        self.cur.execute("""SELECT tag_id FROM link_tag_connections WHERE link_id=?""", (id, ))
        for tag_id in self.cur.fetchall():
            self.cur.execute("""SELECT name FROM tags WHERE id=?""", (tag_id[0], ))
            link.tags.append(self.cur.fetchone()[0])
            link.tags.sort()
        return link

    @db_access
    def get_link_by_url(self, url):
        "Return a Link from the database if one exists with the given URL, otherwise return None."
        self.cur.execute("""SELECT * FROM links WHERE url=?""", (url, ))
        row = self.cur.fetchone()
        if row:
            return Link(*row)
        return None

    @db_access
    def delete_link_by_id(self, id):
        "Delete the link with the given id from the database."
        self.cur.execute("""DELETE FROM links WHERE id=?""", (id, ))
        self.cur.execute("""SELECT tag_id FROM link_tag_connections WHERE link_id=?""", (id, ))
        tag_ids = self.cur.fetchall()
        self.cur.execute("""DELETE FROM link_tag_connections WHERE link_id=?""", (id, ))
        # Delete any tags for which this link was the last link tagged as such
        for tag_id in tag_ids:
            self.kill_unused_tag(tag_id)

    @db_access
    def kill_unused_tag(self, tag_id):
        "Delete a tag if it is not connected to any links."
        self.cur.execute("""SELECT COUNT(tag_id) FROM link_tag_connections WHERE tag_id=?""", (tag_id, ))
        if self.cur.fetchone()[0] is 0:
            self.cur.execute("""DELETE FROM tags WHERE id=?""", (tag_id, ))

    @db_access
    def get_latest_links(self):
        "Return a list of the most recently created Link objects."
        self.cur.execute("""SELECT id FROM links ORDER BY created DESC LIMIT 20""")
        return [self.get_link_by_id(id[0]) for id in self.cur.fetchall()]

    @db_access
    def get_all_tags_and_counts(self):
        "Return a list of all tags in the database, and a list of the number of links with each tag."
        self.cur.execute("""SELECT tags.name, COUNT(tags.id)  FROM tags INNER JOIN link_tag_connections ON tags.id = link_tag_connections.tag_id GROUP BY tags.id ORDER BY COUNT(tags.id) DESC""")
        tc = self.cur.fetchall()
        # Unzip two lists...wish there was a less ugly way to do this!
        return [t[0] for t in tc], [t[1] for t in tc]
       
    @db_access
    def get_links_by_tag_name(self, tag_name):
        "Return a list of all Link objects which have the specified tag"
        self.cur.execute("""SELECT id FROM tags WHERE name=?""", (tag_name,))
        tag_id = self.cur.fetchall()
        if not tag_id:
            return []
        self.cur.execute("""SELECT links.id FROM links INNER JOIN link_tag_connections ON links.id = link_tag_connections.link_id WHERE link_tag_connections.tag_id=? ORDER BY links.created DESC""", (tag_id[0][0],))
        return [self.get_link_by_id(id[0]) for id in self.cur.fetchall()]

    @db_access
    def search(self, searchstring):
        "Return a list Link objects whose title matches the searchstring"
        self.cur.execute("""SELECT id FROM links WHERE title LIKE ?""", ("%%%s%%" % searchstring,))
        return [self.get_link_by_id(id[0]) for id in self.cur.fetchall()]

