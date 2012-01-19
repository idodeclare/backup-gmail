#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__))+ '/..')
import unittest
import backup_gmail

# Roman numeral code is taken from "Dive Into Python", by Mark Pilgrim, 
# copyright 2001, mark@diveintopython.org

class UIDconverterTest(unittest.TestCase):

	class RomanError(Exception): pass
	class OutOfRangeError(RomanError): pass

	romanNumeralMap = (('M', 1000),
		('CM', 900),
		('D', 500),
		('CD', 400),
		('C', 100),
		('XC', 90),
		('L', 50),
		('XL', 40),
		('X', 10),
		('IX', 9),
		('V', 5),
		('IV', 4),
		('I', 1))
		
	def setUp(self):	
		pass
		
	def tearDown(self):
		pass
		
	def toRoman(self, value):
		n = int(value)
		if not (0 < n < 5000):
			raise self.OutOfRangeError(str(value))
			
		result = ""
		for numeral, i in UIDconverterTest.romanNumeralMap:
			while n >= i:
				result += numeral
				n -= i
		return result
		
	def uidsToRoman(self, uid):
		if uid.find(':') == -1:
			return [self.toRoman(uid)]
		else:
			v0, vn = map(int, uid.split(':'))
			result = []
			while v0 <= vn:
				result.append(self.toRoman(v0))
				v0 = 1 + v0
			return result
		
	def testString1(self):
		cfunc = backup_gmail.UIDconverter(UIDconverterTest.uidsToRoman)
		r = cfunc(self, '1')
		expected = 'I'
		self.assertEqual(expected, r)

	def testString2(self):
		cfunc = backup_gmail.UIDconverter(UIDconverterTest.uidsToRoman)
		r = cfunc(self, '101:103')
		expected = ['CI', 'CII', 'CIII']
		self.assertEqual(expected, r)

	def testInts1(self):
		cfunc = backup_gmail.UIDconverter(UIDconverterTest.uidsToRoman)
		r = cfunc(self, [])
		expected = []
		self.assertEqual(expected, r)

	def testInts2(self):
		cfunc = backup_gmail.UIDconverter(UIDconverterTest.uidsToRoman)
		r = cfunc(self, [9, 10])
		expected = ['IX', 'X']
		self.assertEqual(expected, r)

	def testInts3(self):
		cfunc = backup_gmail.UIDconverter(UIDconverterTest.uidsToRoman)
		r = cfunc(self, [9, 11])
		expected = ['IX', 'XI']
		self.assertEqual(expected, r)

	def testInts4(self):
		cfunc = backup_gmail.UIDconverter(UIDconverterTest.uidsToRoman)
		r = cfunc(self, [9, 10, 11, 12, 13])
		expected = ['IX', 'X', 'XI', 'XII', 'XIII']
		self.assertEqual(expected, r)

	def testInts5(self):
		cfunc = backup_gmail.UIDconverter(UIDconverterTest.uidsToRoman)
		r = cfunc(self, [9, 10, 11, 13])
		expected = ['IX', 'X', 'XI', 'XIII']
		self.assertEqual(expected, r)

if __name__ == '__main__':
	unittest.main()