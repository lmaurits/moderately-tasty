import collections
import functools
import sqlite3
import urlparse
import time

import feedformatter
from flask import Flask, request, render_template, redirect, url_for, Response

from modtasty import ModTasty, Link

app = Flask(__name__)
mt = ModTasty()

# Authentication wrapping
####################################################################

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not mt.check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# Flask app proper
####################################################################

@app.route('/')
def index():
    "Home page.  Just shows most recently added links."
    links = mt.get_latest_links()
    for link in links:
        print link.tags
    return render_template("index.html", links=links)

@app.route('/add', methods=['GET', 'POST'])
@requires_auth
def add_link():
    "Web form to add a new link."
    if request.method == "GET":
        return render_template("add.html")
    elif request.method == "POST":
        url = request.form["url"]
        # Check for duplicates
        link = mt.get_link_by_url(url)
        if link:
            return redirect(url_for("view_link", link_id=link.id))
        link = mt.make_link_from_url(url)
        mt.save_link(link)
        return redirect(url_for("edit_link", link_id=link.id))
   
@app.route('/view/<int:link_id>')
def view_link(link_id):
    "Page which shows the particulars of a link."
    link = mt.get_link_by_id(link_id)
    if link:
        return render_template("view.html", link=link)
    else:
        return render_template("error404.html", link=link), 404

@app.route('/edit/<int:link_id>', methods=["GET", "POST"])
@requires_auth
def edit_link(link_id):
    "Web form to edit an exisitng link."
    link = mt.get_link_by_id(link_id)
    if not link:
        return render_template("error404.html", link=link), 404
    if request.method == "GET":
        tags, counts = mt.get_all_tags_and_counts()
        return render_template("edit.html", link=link, tags=tags)
    elif request.method == "POST":
        link = Link(link.id, request.form["title"], request.form["url"], link.created)
        link.tags = [t.strip().lower() for t in request.form["tags"].split(",")]
        mt.save_link(link)
        return redirect(url_for("view_link", link_id=link.id))

@app.route('/del/<int:link_id>', methods=["GET", "POST"])
@requires_auth
def delete_link(link_id):
    "Web form to delete an exisitng link."
    link = mt.get_link_by_id(link_id)
    if not link:
        return render_template("error404.html", link=link), 404
    if request.method == "GET":
        return render_template("delete.html", link=link)
    elif request.method == "POST":
        mt.delete_link_by_id(link_id)
        return redirect(url_for("index"))

@app.route('/tags')
def list_tags():
    "A list of all current tags in the database."
    tags, counts = mt.get_all_tags_and_counts()
    return render_template("all_tags.html", tags_counts=zip(tags, counts))

@app.route('/tag/<tag_name>')
def list_tag(tag_name):
    "A list of all links in the database which have a given tag."
    links = mt.get_links_by_tag_name(tag_name)
    return render_template("tag_list.html", links=links, tag=tag_name)

@app.route('/feed')
def feed():
    "An Atom feed of the most recently created links."
    feed = feedformatter.Feed()
    feed.feed["author"] = "Moderately Tasty"
    for link in mt.get_latest_links():
        item = {}
        item["title"] = link.title
        item["link"] = link.url
        item["pubdate"] = link.created
        feed.items.append(item)
    return feed.format_atom_string()

if mt.email_errors:
    import logging
    from logging.handlers import SMTPHandler
    mail_handler = SMTPHandler('127.0.0.1',
                               'noreply@moderatelytasty.com',
                               [mt.admin_email], 'Moderately Tasty Failed')
    mail_handler.setLevel(logging.ERROR)
    app.logger.addHandler(mail_handler)

if __name__ == '__main__':
    app.run(debug=True)

