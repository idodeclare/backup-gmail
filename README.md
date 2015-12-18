# backup_gmail #

Copyright 2011, Joseph Wen

Copyright 2015, Chris Fraire

This application provides both a command line interface and graphical user
interface to backup and restore Gmail data via IMAP. It support incremental
backup based on message-id and sha1. It also preserves the read/unread state
on the Gmail server.

For more information visit:
https://github.com/idodeclare/backup-gmail

Usage 
=====
./backup_gmail.py

or

./gui.py

Caveats 
=======

Time Zones
----------
  A backup operation processes --start and --end using Gmail's servers,
and time zones are respected; dates will be qualified using the user's
configured Gmail time zone.

  --mbox_export and --restore, however, do not currently respect time 
zones for --start and --end, so results can be slightly incorrect near
the date range boundaries.


Additional Libraries 
====================

The Qt library, used by gui.py, may need to be installed for platforms
where it is not available by default (e.g., Mac OS X, Windows, etc.):

  http://qt.nokia.com/downloads

PySide for Qt, used by gui.py, is available for various platforms at:

  http://developer.qt.nokia.com/wiki/PySideDownloads

keyring for Python, used for secure storage of passwords, is available at:

  http://pypi.python.org/pypi/keyring#downloads
