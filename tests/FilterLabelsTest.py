#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__))+ '/..')
import unittest
import re
import backup_gmail

class FilterLabelsTest(unittest.TestCase):
	uinput = ['Acorn', 'Chariot', 'coöperate', 'INBOX']

	def setUp(self):	
		pass
		
	def tearDown(self):
		pass

	def testDefault(self):
		f = backup_gmail.FilterLabels(None, None, None, None)
		r = f.filter(self.uinput)
		expected = self.uinput
		self.assertEqual(expected, r)
		
	def testInclude1(self):
		f = backup_gmail.FilterLabels(['inBox'], None, None, None)
		r = f.filter(self.uinput)
		expected = ['INBOX']
		self.assertEqual(expected, r)

	def testExclude1(self):
		f = backup_gmail.FilterLabels(None, ['inBox'], None, None)
		r = f.filter(self.uinput)
		expected = ['Acorn', 'Chariot', 'coöperate']
		self.assertEqual(expected, r)

	def testStrictExclude1(self):
		f = backup_gmail.FilterLabels(None, ['inBox'], True, None)
		r = f.filter(self.uinput)
		expected = []
		self.assertEqual(expected, r)

	def testRegex1(self):
		f = backup_gmail.FilterLabels(None, None, None, r'^[C]')
		r = f.filter(self.uinput)
		expected = ['Chariot', 'coöperate']
		self.assertEqual(expected, r)

	def testRegex2(self):
		f = backup_gmail.FilterLabels(None, None, None, r'ö')
		r = f.filter(self.uinput)
		expected = ['coöperate']
		self.assertEqual(expected, r)

if __name__ == '__main__':
	unittest.main()