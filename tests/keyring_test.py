#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__))+ '/..')
import backup_gmail
import getpass

if __name__ == '__main__':
	username = None
	while username is None or username == '':
		username = raw_input('Username: ')
	password = None
	while password is None or password == '':
		password = getpass.getpass()

	keyu = backup_gmail.KeyringUtil('keyring_test.py (%s)')
	stored = keyu.get_password(username)
	print "Stored password: ", stored
	keyu.set_password(username, password)
	print "<called set_password>"
	stored = keyu.get_password(username)
	print "Stored password: ", stored
