#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__))+ '/..')
import unittest
import backup_gmail
import locale

def theTestSuite():
	return unittest.TestLoader().loadTestsFromTestCase(GmailDateTest)

class GmailDateTest(unittest.TestCase):

	@classmethod
	def setUpClass(cls):
		cls.origlocale = locale.getlocale(locale.LC_TIME)
		
	@classmethod
	def tearDownClass(cls):
		locale.setlocale(locale.LC_TIME, cls.origlocale)

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
