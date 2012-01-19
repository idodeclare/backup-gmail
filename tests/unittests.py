#!/usr/bin/env python

import unittest
import UIDconverterTest
import FilterLabelsTest
import GmailDateTest

if __name__ == "__main__":
  alltests = unittest.TestSuite()
  alltests.addTest(UIDconverterTest.theTestSuite()) 
  alltests.addTest(FilterLabelsTest.theTestSuite()) 
  alltests.addTest(GmailDateTest.theTestSuite()) 
  unittest.TextTestRunner(verbosity=2).run(alltests)