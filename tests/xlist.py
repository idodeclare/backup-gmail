import sys
import backup_gmail
from optparse import OptionParser

if __name__ == '__main__':
	parser = OptionParser()
	(options, args) = parser.parse_args()
	if len(args) < 2:
		print 'xlist.py <username> <password>'
		exit()

	gm = backup_gmail.Gmail(args[0], args[1])
	gm.login()
	try:
		res = gm.fetchSpecialLabels();
		print res
	finally:
		gm.close()