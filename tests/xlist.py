#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__))+ '/..')
import backup_gmail
import getpass

class MyOptions: pass

if __name__ == '__main__':
	options = MyOptions()
	options.username = None
	while not options.username:
		options.username = raw_input('Username: ')
	options.password = None
	while not options.password:
		options.password = getpass.getpass()

	gm = backup_gmail.Gmail(options)
	gm.login()
	res = gm.fetchSpecialLabels();
	print res
