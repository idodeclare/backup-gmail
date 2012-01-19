#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__))+ '/..')
import unittest
import backup_gmail
import locale

class TestGmailDate(unittest.TestCase):

	def setUp(self):
		self.origlocale = locale.getlocale(locale.LC_TIME)
		
	def tearDown(self):
		locale.setlocale(locale.LC_TIME, self.origlocale)

	def testToLocal(self):
		locale.setlocale(locale.LC_TIME, 'de_DE')
		ldate = backup_gmail.GmailDate.toLocal('1-Mar-2012')
		self.assertEqual('01-Mär-2012', ldate)
		
	def testFromLocal(self):
		locale.setlocale(locale.LC_TIME, 'de_DE')
		gdate = backup_gmail.GmailDate.fromLocal('1-Mär-2012')
		self.assertEqual('01-Mar-2012', gdate)
	
if __name__ == '__main__':
	unittest.main()