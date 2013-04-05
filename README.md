moderately-tasty
================

A minimal, single user Delicio.us replacement

# Intro

Moderately Tasty is a bare-bones bookmarking app with tag support, built using Flask and SQLite.  It's a single user application: you install an instance for yourself on your own server and you're the only person who uses it.  If someone wants to "follow" you, they can subscribe to an Atom feed.  That's about as "social" as MT gets.

MT is aimed at people who really just use Delicio.us or similar sites as a way to keep their own bookmarks easily accessible from anywhere, and want to be able to do this without relying on a third party web application which may be shutdown, sold or drastically changed at any time.

# Dependencies

MT requires:
* [Flask](https://github.com/mitsuhiko/flask)
* [BeautifulSoup](https://githuboftware/BeautifulSoup/)
* [FeedFormatter](https://code.google.com/p/feedformatter/)
all of which are available via PyPI.

# Installation

modtasty.fcgi provides a FastCGI wrapper around the WSGI app in flaskapp.py, so MT should be easily deployable in any environment that support FastCGI.

1. Change to somewhere in your webserver's document root (e.g. `/srv/www/modtasty`)
2. Clone the MT repository: `git clone https://github.com/lmaurits/moderately-tasty.git`
3. Copy the file `config.py.example` to `config.py` (unless you're happy with all default settings)
4. Configure your webserver to start `modtasty.fcgi` as a FastCGI process and send requests to it

Note that the FastCGI process must have write permission to the `moderately-tasty` directory and the database file (`modtasty.db`) or else you'll get mysterious Error 500 pages.

# Configuration

## Permissions

By default, anybody can see your bookmarks, tags, etc. but will need to provide credentials to add, edit or delete bookmarks.  Authentication is currently done simply using HTTP Basic Authentication, so if security is really important please use HTTPS.  You can fine-tune permissions using the following options in `config.py`:

    USERNAME = "modtasty"
    PASSWORD = "modtasty"
    PUBLIC_READ = True
    PUBLIC_WRITE = False
    PUBLIC_FEED = True

By changing the various `PUBLIC_*` settings, you can make your MT install completely public (set all options to `True`), completely private (set all options to `False`), or anywhere inbetween.  `USERNAME` and `PASSWORD` do exactly what you'd expect them to.

# Problem?

Please report bugs using the issue tracker at https://github.com/lmaurits/moderately-tasty/issues or via email to <luke@maurits.id.au>.
