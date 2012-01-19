import sys
import backup_gmail
from optparse import OptionParser

if __name__ == '__main__':
	parser = OptionParser()
	(options, args) = parser.parse_args()
	if len(args) < 2:
		print 'keyring_test.py <username> <password>'
		exit()

	username = args[0]
	password = args[1]
	
	keyu = backup_gmail.KeyringUtil()
	stored = keyu.get_password(username)
	print "Stored password: ", stored
	keyu.set_password(username, password)
	print "<called set_password>"
	stored = keyu.get_password(username)
	print "Stored password: ", stored
