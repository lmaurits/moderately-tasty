moderately-tasty
================

A minimal, single user Delicio.us replacement

Moderately Tasty is a bare-bones bookmarking app with tag support, 
built using Flask and SQLite.  It's a single user application: you install an
instance for yourself on your own server and you're the only person who uses
it.  If someone wants to "follow" you, they can subscribe to an Atom feed.
That's about as "social" as MT gets.

modtasty.fcgi provides a FastCGI wrapper around the WSGI app in flaskapp.py,
so MT should be easily deployable in any environment that support FastCGI.

Note that the FastCGI process must have write permission to the
moderately-tasty directory and the database file (modtasty.db) or else you'll
get mysterious Error 500 pages.
