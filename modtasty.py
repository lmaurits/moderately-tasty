import collections
import sqlite3
import urlparse
import time

import requests
from BeautifulSoup import BeautifulSoup

from flask import Flask, request, render_template, redirect, url_for

app = Flask(__name__)

class Link():
    
    def __init__(self, title="Untitled", url=None):
        self.id = None
        self.title = title
        self.url = url
        self.created = None
        self.tags = []

    def datetime(self):
        return time.strftime("%d %b %Y", time.gmtime(self.created))

    def domain(self):
        return urlparse.urlparse(self.url).netloc

    def prettytitle(self):
        if self.title:
            return self.title
        else:
            return "Untitled (%s)" % self.url

def make_link_from_table_row(row):
    link = Link()
    link.id = row[0]
    link.title = row[1]
    link.url = row[2]
    link.created = row[3]
    return link

def initialise_db():
    con = sqlite3.connect("tasty.db")
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY ASC,
            title TEXT,
            url TEXT,
            created INTEGER
            )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY ASC,
            name TEXT
            )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS link_tag_connections (
            link_id INTEGER,
            tag_id INTEGER,
            FOREIGN KEY(link_id) REFERENCES links(id),
            FOREIGN KEY(tag_id) REFERENCES tags(id)
            )""")

    con.commit()
    cur.close()
    con.close()

def make_link_from_url(url):
    link = Link(url=url)
    r = requests.get(url)
    s = BeautifulSoup(r.text)
    link.title = s.title.string
    return link

def save_link(link):
    con = sqlite3.connect("tasty.db")
    cur = con.cursor()

    if not link.created:
        link.created = time.time()
    if link.id:
        cur.execute("""UPDATE links SET title=?, url=? WHERE id=?""", (link.title, link.url, link.id))
    else:
        cur.execute("""INSERT INTO links (title, url, created) VALUES (?, ?, ?)""", (link.title, link.url, link.created))
        cur.execute("""SELECT id FROM links WHERE url=?""", (link.url,))
        link.id = cur.fetchone()[0]

    cur.execute("""DELETE from link_tag_connections WHERE link_id=?""", (link.id,))
    for tag in link.tags:
        cur.execute("""SELECT id FROM tags WHERE name=?""", (tag,))
        tag_id = cur.fetchall()
        if tag_id:
            tag_id = tag_id[0][0]
            cur.execute("""INSERT INTO link_tag_connections VALUES (?, ?)""", (link.id, tag_id))
        else:
            cur.execute("""INSERT INTO tags (name) VALUES (?)""", (tag, ))
            cur.execute("""SELECT id FROM tags WHERE name=?""", (tag, ))
            tag_id = cur.fetchone()[0]
            cur.execute("""SELECT id FROM tags WHERE name=?""", (tag, ))
            cur.execute("""INSERT INTO link_tag_connections VALUES (?, ?)""", (link.id, tag_id))

    con.commit()
    cur.close()
    con.close()

def get_link_by_id(id):
    con = sqlite3.connect("tasty.db")
    cur = con.cursor()
    cur.execute("""SELECT * FROM links WHERE id=?""", (id, ))
    link = make_link_from_table_row(cur.fetchone())
    cur.execute("""SELECT tag_id FROM link_tag_connections WHERE link_id=?""", (id, ))
    for tag_id in cur.fetchall():
        tag_id = tag_id[0]
        cur.execute("""SELECT name FROM tags WHERE id=?""", (tag_id, ))
        link.tags.append(cur.fetchone()[0])
        link.tags.sort()
    cur.close()
    con.close()
    return link

def delete_link_by_id(id):
    con = sqlite3.connect("tasty.db")
    cur = con.cursor()
    cur.execute("""DELETE FROM links WHERE id=?""", (id, ))
    cur.execute("""DELETE FROM link_tag_connections WHERE link_id=?""", (id, ))
    # TODO check if we just deleted the last link for any tag and if so del tag
    con.commit()
    cur.close()
    con.close()

def get_latest_links():
    con = sqlite3.connect("tasty.db")
    cur = con.cursor()
    cur.execute("""SELECT id FROM links ORDER BY created DESC LIMIT 20""")
    links = [get_link_by_id(id[0]) for id in cur.fetchall()]
    cur.close()
    con.close()
    return links

def get_all_tags_and_counts():
    con = sqlite3.connect("tasty.db")
    cur = con.cursor()
    cur.execute("""SELECT tags.name, COUNT(tags.id)  FROM tags INNER JOIN link_tag_connections ON tags.id = link_tag_connections.tag_id GROUP BY tags.id ORDER BY COUNT(tags.id) DESC""")
    tc = cur.fetchall()
    tags = [t[0] for t in tc]
    counts = [t[1] for t in tc]
    cur.close()
    con.close()
    return tags, counts
   
# SELECT tag, COUNT(tag)  FROM tags INNER JOIN tag_post_links ON tags.id = tag_post_links.tag_id GROUP BY tag ORDER BY tag ASC
def get_links_by_tag_name(tag_name):
    con = sqlite3.connect("tasty.db")
    cur = con.cursor()
    cur.execute("""SELECT id FROM tags WHERE name=?""", (tag_name,))
    tag_id = cur.fetchall()
    if not tag_id:
        return []
    cur.execute("""SELECT links.id FROM links INNER JOIN link_tag_connections ON links.id = link_tag_connections.link_id WHERE link_tag_connections.tag_id=? ORDER BY links.created DESC""", (tag_id[0][0],))
    links = [get_link_by_id(id[0]) for id in cur.fetchall()]
    cur.close()
    con.close()
    return links

@app.route('/')
def index():
    links = get_latest_links()
    for link in links:
        print link.tags
    return render_template("index.html", links=links)

@app.route('/add', methods=['GET', 'POST'])
def add_link():
    if request.method == "GET":
        return render_template("add.html")
    elif request.method == "POST":
        url = request.form["url"]
        link = make_link_from_url(url)
        save_link(link)
        return redirect(url_for("edit_link", link_id=link.id))
   
@app.route('/view/<int:link_id>')
def view_link(link_id):
    link = get_link_by_id(link_id)
    return render_template("view.html", link=link)

@app.route('/edit/<int:link_id>', methods=["GET", "POST"])
def edit_link(link_id):
    link = get_link_by_id(link_id)
    if request.method == "GET":
        tags, counts = get_all_tags_and_counts()
        return render_template("edit.html", link=link, tags=tags)
    elif request.method == "POST":
        link = make_link_from_table_row([link.id, request.form["title"], request.form["url"], link.created])
        link.tags = [t.strip().lower() for t in request.form["tags"].split(",")]
        save_link(link)
        return redirect(url_for("view_link", link_id=link.id))

@app.route('/del/<int:link_id>', methods=["GET", "POST"])
def delete_link(link_id):
    link = get_link_by_id(link_id)
    if request.method == "GET":
        return render_template("delete.html", link=link)
    elif request.method == "POST":
        delete_link_by_id(link_id)
        return redirect(url_for("index"))

@app.route('/tags')
def list_tags():
    tags, counts = get_all_tags_and_counts()
    return render_template("all_tags.html", tags_counts=zip(tags, counts))

@app.route('/tag/<tag_name>')
def list_tag(tag_name):
    links = get_links_by_tag_name(tag_name)
    return render_template("tag_list.html", links=links, tag=tag_name)

if __name__ == '__main__':
    initialise_db()
    app.run(debug=True)

