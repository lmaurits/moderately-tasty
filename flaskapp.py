import collections
import sqlite3
import urlparse
import time

import feedformatter
from flask import Flask, request, render_template, redirect, url_for

from modtasty import ModTasty

app = Flask(__name__)
mt = ModTasty()

@app.route('/')
def index():
    links = mt.get_latest_links()
    for link in links:
        print link.tags
    return render_template("index.html", links=links)

@app.route('/add', methods=['GET', 'POST'])
def add_link():
    if request.method == "GET":
        return render_template("add.html")
    elif request.method == "POST":
        url = request.form["url"]
        link = mt.make_link_from_url(url)
        save_link(link)
        return redirect(url_for("edit_link", link_id=link.id))
   
@app.route('/view/<int:link_id>')
def view_link(link_id):
    link = mt.get_link_by_id(link_id)
    return render_template("view.html", link=link)

@app.route('/edit/<int:link_id>', methods=["GET", "POST"])
def edit_link(link_id):
    link = mt.get_link_by_id(link_id)
    if request.method == "GET":
        tags, counts = mt.get_all_tags_and_counts()
        return render_template("edit.html", link=link, tags=tags)
    elif request.method == "POST":
        link = mt.make_link_from_table_row([link.id, request.form["title"], request.form["url"], link.created])
        link.tags = [t.strip().lower() for t in request.form["tags"].split(",")]
        mt.save_link(link)
        return redirect(url_for("view_link", link_id=link.id))

@app.route('/del/<int:link_id>', methods=["GET", "POST"])
def delete_link(link_id):
    link = mt.get_link_by_id(link_id)
    if request.method == "GET":
        return render_template("delete.html", link=link)
    elif request.method == "POST":
        mt.delete_link_by_id(link_id)
        return redirect(url_for("index"))

@app.route('/tags')
def list_tags():
    tags, counts = mt.get_all_tags_and_counts()
    return render_template("all_tags.html", tags_counts=zip(tags, counts))

@app.route('/tag/<tag_name>')
def list_tag(tag_name):
    links = mt.get_links_by_tag_name(tag_name)
    return render_template("tag_list.html", links=links, tag=tag_name)

@app.route('/feed')
def feed():
    feed = feedformatter.Feed()
    feed.feed["author"] = "Moderately Tasty"
    for link in mt.get_latest_links():
        item = {}
        item["title"] = link.title
        item["link"] = link.url
        item["pubdate"] = link.created
        feed.items.append(item)
    return feed.format_atom_string()

if __name__ == '__main__':
    app.run(debug=True)

