moderately-tasty
================

A minimal, single user Delicio.us replacement

Moderately Tasty is a bare-bones bookmark tagging webapp built using Flask and
SQLight.  It's a single user application, with no social component: you
install it on your server and use it from there. 

modtasty.fcgi provides a FastCGI wrapper around the WSGI app in modtasty.py,
so MT should be easily deployable in any environment that support FastCGI.
