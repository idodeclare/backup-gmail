#!/usr/bin/python

import sys
import locale
import backup_gmail

if __name__ == '__main__':
  locale.setlocale(locale.LC_TIME, '')
  d = sys.argv[1]
  i = backup_gmail.GmailDate.toLocal(d)
  print i
  l = backup_gmail.GmailDate.fromLocal(i)  
  print l
  b = backup_gmail.GmailDate.toLocal(l)
  print b
