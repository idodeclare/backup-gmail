#!/usr/bin/python

"""
Copyright 2011, Joseph Wen
"""

#TODO: MailBox

import imaplib
import traceback
import email.message, email.utils
import re, sys, hashlib, os, shutil, time, optparse, mailbox, copy
from datetime import datetime
import ConfigParser

class MailMetaData:
	@classmethod
	def fromStr(cls, s):
		tmp = re.split(' ', s, 4)
		m = cls(tmp[0])
		m.folder = tmp[1]
		m.hash_value = tmp[2]
		m.seen = tmp[3] == "True"
		m.labels = set()
		if len(tmp) > 4:
			m.labels = set(tmp[4].split(" ^ "))
		return m


	def __init__(self, id, hash_value = None, folder = None):
		self.id = id
		self.seen = False
		self.labels = set()
		self.hash_value = hash_value
		self.folder = folder
	
	def getMail(self, dest):
		with open('%s/%s/%s' % (dest, self.folder, self.hash_value)) as f:
			return email.message_from_string(f.read())
	
	def __str__(self):
		return "%s %s %s %s %s" % (self.id, self.folder, self.hash_value, str(self.seen), " ^ ".join(self.labels))

def getMID(env):
	tmp = re.findall('(<[^>]+>)', env)
	if len(tmp) == 0:
		return None
	return tmp[0]

def getUID(env):
	return re.findall('^([0-9]+)', env)[0]

def UIDconverter(func):
	def convert(self, uid):
		if isinstance(uid, str):
			data = func(self, uid)
			return data if uid.find(':') != -1 else data[0]
		uids = sorted(map(int, uid))
		result = []
		if len(uids) == 0: 
			return result
		start = end = uids[0]
		for i in uids[1:]:
			if end + 1 == i:
				end = i
			else:
				result += func(self, "%d:%d" % (start, end))
				start = end = i
		result += func(self, "%d:%d" % (start, end))
		return result

	return convert

class Gmail(object):
	class AuthError(Exception):
		def __init__(self, str):
			self.str = str

		def __str__(self):
			return repr(self.str)
	
	class SelectMailBoxError(Exception):
		def __init__(self, str, l):
			self.str = str
			self.l = l

		def __str__(self):
			return "MailBox [%s] does not exists.\nMailBox List: %s" % (self.str, self.l)

	def __init__(self, username, password):
		self.gmail_prefix = None
		self.gmail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
		try:
			ret, message = self.gmail.login(username, password)
		except Exception as e:
			raise self.AuthError("username or password incorrect")

	def resultCountCheck(self, result, number):
		if number.find(':') == -1:
			return len(result) == 1
		else:
			l = number.split(':')
			return len(result) == int(l[1]) - int(l[0]) + 1

	@UIDconverter
	def fetchRFC822(self, uid):
		data = []
		while not self.resultCountCheck(data, uid):
			ret, data = self.gmail.fetch(uid, 'RFC822')
			data = filter(lambda x: len(x) == 2, data)
			data = map(lambda x:(getUID(x[0]), x[1]), data)
		return data

	@UIDconverter
	def fetchMessageId(self, uid):
		data = []
		while not self.resultCountCheck(data, uid):
			ret, data = self.gmail.fetch(uid, '(BODY[HEADER.FIELDS (MESSAGE-ID)])')
			data = filter(lambda x: len(x) == 2, data)
			data = map(lambda x:(getUID(x[0]), getMID(x[1])), data)
		return data

	@UIDconverter
	def fetchRFC822Info(self, uid): # return UID, SIZE, SEEN
		data = []
		while not self.resultCountCheck(data, uid):
			ret, data = self.gmail.fetch(uid, '(RFC822.SIZE FLAGS)')
			data = map(lambda x : (getUID(x), re.findall('RFC822.SIZE ([0-9]+)', x)[0], re.search("Seen", x) != None), data)
		return data

	def searchByDate(self, start, end = None):
		if start == None and end == None:
			ret, result = self.gmail.search(None, 'ALL')
			return result[0].split()
		elif end == None:
			ret, result = self.gmail.search(None, '(SINCE "%s")' % (start, ))
			return result[0].split()
		elif start == None:
			ret, result = self.gmail.search(None, '(BEFORE "%s")' % (end, ))
			return result[0].split()
		else:
			ret, result = self.gmail.search(None, '(SINCE "%s") (BEFORE "%s")' % (start, end))
			return result[0].split()

	def fetchLabelNames(self):
		labels = self.gmail.list()[1]
		return map(lambda x:x[0], 
			filter(lambda x : len(x) > 0, 
			map(lambda x : re.findall('\(\\\\HasNoChildren\) "/" "([^"]+)"', x), labels)))

	def selectMailBox(self, name):
		ret, mail_count = self.gmail.select(name)
		if ret == 'NO':
			raise self.SelectMailBoxError(name, self.fetchLabelNames())
		return mail_count

	def getGmailPrefix(self):
		if self.gmail_prefix != None:
			return self.gmail_prefix
		labels = self.fetchLabelNames()
		prefixs = filter(lambda x: x.find('/All Mail') != -1, labels)
		if len(prefixs) == 0:
			raise self.SelectMailBoxError('<All Mail>', labels)

		p = prefixs[0].split('/')[0]
		if len(prefixs) > 1:
			print "There are multiple possible prefixs for Gmail mailbox use [%s]" % (p, )
		self.gmail_prefix = p
		return self.gmail_prefix

	def setFlag(self, uid, flag):
		self.gmail.store(uid, '+Flags', flag)
	
	def unsetFlag(self, uid, flag):
		self.gmail.store(uid, '-Flags', flag)

class BackupGmail(Gmail):
	def __init__(self, username, password, dest, progress = None):
		super(BackupGmail, self).__init__(username, password)
		self.mboxs = {}
		self.mails = {}
		self.keep_read_status = False
		self.progress = progress
		self.dest = dest
		self.exclude_mids = set()

		self.fetchBuffer = []
		self.fetchStart = '-1'
		self.fetchEnd = '-1'
		self.fetchSize = 0

	def addToMBox(self, label, mail):
		if label not in self.mboxs:
			self.mboxs[label] = mailbox.mbox('%s/%s.mbox' % (self.dest, label.replace('/', '-'), ), create = True)
		self.mboxs[label].add(mail)

	def initProgress(self, infos):
		total = sum(map(lambda x:int(x[1]), infos))
		self.progress.setRange(0, total)
		self.progress.setValue(0)

	def fetchMailByLabel(self, label, date_range):
		self.progress.setText("\rFetching %s [calculate size]                           \r" % (label, ))
		mail_count = self.selectMailBox(label)
		if date_range[0] == None and date_range[1] == None:
			infos = self.fetchRFC822Info('1:%s' % (mail_count[0], ))
			envs = self.fetchMessageId('1:%s' % (mail_count[0], ))
		else:
			date_range = self.searchByDate(*date_range)
			infos = self.fetchRFC822Info(date_range)
			envs = self.fetchMessageId(date_range)

		self.progress.setText("\rFetching %s [@value/@max]                           \r" % (label, ))
		self.initProgress(infos)
		total = 0

		for i, (env, info) in enumerate(zip(envs, infos)):
			uid, mid = env
			uid, size, seen = info
			if mid not in self.mails:
				if mid not in self.exclude_mids:
					self.fetchMail(uid, seen, label, size)
			else:
				self.mails[mid].labels.add(label)
				self.addToMBox(label, self.mails[mid].getMail(self.dest))
				if seen == False and self.keep_read_status:
					self.unsetFlag(uid, '\\Seen')
			total += int(size)
			self.progress.setValue(total)
			
		#Flush all pending request
		self.flushFetchMailRequest()

	def processMail(self, rfc, seen, label):
		mail = email.message_from_string(rfc)
		date = email.utils.parsedate(mail.get('date'))
		if date == None or len(date) != 9:
			fold = "Date-Unknown"
		else:
			fold = time.strftime("%Y-%m", date)
		h = hashlib.sha256(rfc).hexdigest()
		mid = mail.get('message-id')
		if mid == None: 
			mid = "<%s@backupgmail.com>" % (h, )
			mail.add_header('message-id', mid)
			rfc = mail.as_string()
			mail = email.message_from_string(rfc)
		try:
			os.mkdir("%s/%s" % (self.dest, fold))
		except OSError as e:
			pass
		with open("%s/%s/%s" % (self.dest, fold, h), 'w') as f:
			f.write(rfc)

		if mid not in self.mails:
			self.mails[mid] = MailMetaData(mid, h, fold)
			self.mails[mid].seen = seen

		self.mails[mid].labels.add(label)
		self.addToMBox(label, mail)

	def flushFetchMailRequest(self):
		if self.fetchBuffer == []:
			return

		rfcs = self.fetchRFC822('%s:%s' % (self.fetchStart, self.fetchEnd))
		if self.keep_read_status:
			for i, rfc in enumerate(rfcs):
				if self.fetchBuffer[i][0] == False:
					self.unsetFlag(rfc[0], '\\Seen')
		for i, rfc in enumerate(rfcs):
			self.processMail(rfc[1], *self.fetchBuffer[i])

		self.fetchBuffer = []
		self.fetchEnd = '-1'
		self.fetchSize = 0

	def fetchMail(self, uid, seen, label, size):
		size = int(size)
		if len(self.fetchBuffer) > 300 or self.fetchSize > 10000000:
			self.flushFetchMailRequest()
		if int(self.fetchEnd) + 1 == int(uid):
			self.fetchEnd = uid
			self.fetchBuffer += [(seen, label)]
			self.fetchSize += size
		else:
			self.flushFetchMailRequest()
			self.fetchStart = uid
			self.fetchEnd = uid
			self.fetchBuffer += [(seen, label)]
			self.fetchSize += size
	
	def fetchAllLabel(self, date_range, exclude_labels = []):
		#FIXME need support for multi lanugage
		#ignore = ['%s/All Mail' % (self.getGmailPrefix(), ),
		#		'%s/Trash' % (self.getGmailPrefix(), ),
	        #   		'%s/Spam' % (self.getGmailPrefix(), )] + exclude_labels
		#labels = filter(lambda x : x not in ignore , self.fetchLabelNames())
		labels = self.fetchLabelNames()

		for l in labels:
			self.fetchMailByLabel(l, date_range)

	def fetchAllMail(self, date_range, exclude_labels = []):
		if exclude_labels != []:
			labels = filter(lambda x : x in exclude_labels, self.fetchLabelNames())
			for l in labels:
				mail_count = self.selectMailBox(l)
				tmp = set(map(lambda x:x[1], self.fetchMessageId("1:%s" % (mail_count[0], ))))
				self.exclude_mids.update(tmp)
		#FIXME need support for multi lanugage
		#self.fetchMailByLabel('%s/All Mail' % (self.getGmailPrefix(), ), date_range)
		self.fetchAllLabel(date_range, exclude_labels)
	
	def outputLable(self):
		with open(self.dest + '/label', 'w') as f:
			for k in self.mails:
				print >> f, self.mails[k]

	def checkDir(self, overwrite):
		try:
			os.mkdir(self.dest)
		except OSError as e:
			if e.errno == 17:
				if overwrite == False:
					s = raw_input("[%s] Already exists overwrite? (use -i for incremental backup) [N/y]" % (e.filename, ))
				else:
					s = 'Y'
				if s == 'Y' or s == 'y' or s == 'yes':
					shutil.rmtree(self.dest)
					os.mkdir(self.dest)
				else:
					exit()
			else:
				raise e
	
	def doBackup(self, date_range = None, include_labels = None, exclude_labels = None):
		try:
			self.mboxs = {}
			if include_labels == None and exclude_labels == None:
				self.fetchAllMail(date_range)
			elif include_labels != None:
				for l in include_labels:
					self.fetchMailByLabel(l, date_range)
			elif exclude_labels != None:
				self.fetchAllMail(date_range, exclude_labels)
		finally:
			self.outputLable()
			for m in self.mboxs:
				self.mboxs[m].flush()

	def backupTo(self, date_range = None, overwrite = False, include_labels = None, exclude_labels = None):
		self.checkDir(overwrite)
		self.doBackup(date_range, include_labels, exclude_labels)

	def incrementalBackupTo(self, date_range = None, include_labels = None, exclude_labels = None):
		try:
			with open("%s/label" % (self.dest, )) as f:
				for line in f.readlines():
					m = MailMetaData.fromStr(line.strip())
					self.mails[m.id] = m
		except:
			self.backupTo(date_range, False, include_labels, exclude_labels)
			return
		self.doBackup(date_range, include_labels, exclude_labels)


class RestoreGmail(Gmail):
	def __init__(self, username, password, src, progress):
		super(RestoreGmail, self).__init__(username, password)
		self.labels = set(self.fetchLabelNames())
		self.progress = progress
		self.src = src
		self.mails = {}

	def appendMessage(self, message, date, mailbox = None):
		ret, msg = self.gmail.append(mailbox, None, date, message)
		return re.findall("APPENDUID [0-9]+ ([0-9]+)", msg[0])[0]

	def assignLabel(self, uid, label):
		#FIXME need support for multi lanugage
		#if label == "%s/All Mail" % (self.getGmailPrefix(), ): return
		if label not in self.labels:
			self.gmail.create(label)
			self.labels = set(self.fetchLabelNames())
		ret, msg = self.gmail.uid('COPY', uid, label)
	
	def isInTimeFrame(self, date_range, date):
		if date == None:
			return True
		if date_range == None or (date_range[0] == None and date_range[1] == None):
			return True
		if date_range[0] == None:
			end = datetime.strptime(date_range[1], "%d-%b-%Y")
			return date < end
		if date_range[1] == None:
			start = datetime.strptime(date_range[0], "%d-%b-%Y")
			return start < date 
		start = datetime.strptime(date_range[0], "%d-%b-%Y")
		end = datetime.strptime(date_range[1], "%d-%b-%Y")
		return start < date and date < end

	def restore(self, date_range = None, include_labels = None, exclude_labels = None):
		with open("%s/label" % (self.src, )) as f:
			for line in f.readlines():
				m = MailMetaData.fromStr(line.strip())
				self.mails[m.id] = m
		
		#FIXME need support for multi lanugage
		#mail_count = self.selectMailBox('%s/All Mail' % (self.getGmailPrefix(), ))
		mail_count = self.selectMailBox('INBOX')
		for i, m in enumerate(self.mails.values()):
			print "\r%d" % (i), 
			sys.stdout.flush()

			include = m.labels.intersection(include_labels) if include_labels != None else m.labels
			exclude = m.labels.intersection(exclude_labels) if exclude_labels != None else set()
			if include_labels != None and include == set():
				continue
			if exclude_labels != None and exclude != set():
				continue
			with open("%s/%s/%s" % (self.src, m.folder, m.hash_value)) as f:
				mail = f.read()
				e = email.message_from_string(mail)
				date = email.utils.parsedate(e.get('date'))
				if date != None and not self.isInTimeFrame(date_range, datetime(*date[:7])):
					continue
				#FIXME need support for multi lanugage
				#uid = self.appendMessage(mail, date, '%s/All Mail' % (self.getGmailPrefix(), ))
				uid = self.appendMessage(mail, date, 'INBOX')
				updateLabel = m.labels.difference(exclude).intersection(include)
				for label in updateLabel:
					self.assignLabel(uid, label)
		print
	
class TerminalProgress:
	def __init__(self):
		self.value = 0
		self.min = 0
		self.max = 0

	def setRange(self, a, b):
		self.min = a
		self.max = b
		self.update()

	def setValue(self, value):
		self.value = value
		self.update()

	def setText(self, t):
		self.text = t
		self.update()
	
	def update(self):
		x = self.text
		x = x.replace('@value', str(self.value))
		x = x.replace('@max', str(self.max))
		print '\r%s' % (x, ),
		sys.stdout.flush()

def loadConfigFile(options, filename):
	config = ConfigParser.SafeConfigParser()
	config.read([filename, os.path.expanduser('~/.backup_gmail.cfg')])
	result = {}
	for section in config.sections():
		result[section] = copy.copy(options)
		result[section].username = config.get(section, 'username')
		result[section].password = config.get(section, 'password')
		result[section].backup_dir = config.get(section, 'backup_dir')
		if config.has_option(section, 'keep_read'):
			result[section].keep_read = config.getboolean(section, 'keep_read')
		if config.has_option(section, 'incremental'):
			result[section].incremental = config.getboolean(section, 'incremental')
		if config.has_option(section, 'start_date'):
			result[section].start_date = config.get(section, 'start_date')
		if config.has_option(section, 'end_date'):
			result[section].end_date = config.get(section, 'end_date')
		if config.has_option(section, 'include_labels'):
			result[section].include_labels = config.get(section, 'include_labels')
		if config.has_option(section, 'exclude_labels'):
			result[section].exclude_labels = config.get(section, 'exclude_labels')
	return result

def saveConfigFile(profiles, filename):
	def set_helper(cfg, section, option, value):
		if value == None:
			return
		return cfg.set(section, option, str(value))
	config = ConfigParser.SafeConfigParser()
	for section in profiles:
		p = profiles[section]
		config.add_section(section)
		set_helper(config, section, 'username', p.username)
		set_helper(config, section, 'password', p.password)
		set_helper(config, section, 'backup_dir', p.backup_dir)
		set_helper(config, section, 'keep_read', p.keep_read)
		set_helper(config, section, 'incremental', p.incremental)
		set_helper(config, section, 'start_date', p.start_date)
		set_helper(config, section, 'end_date', p.end_date)
		set_helper(config, section, 'include_labels', p.include_labels)
		set_helper(config, section, 'exclude_labels', p.exclude_labels)
	with open(filename, 'w') as f:
		config.write(f)

def getOptionParser():
	parser = optparse.OptionParser(usage = "%prog backup_dir email@address password")
	parser.add_option("-r", "--restore", dest="restore", action="store_true", default = False, help = "Restore backup to online gmail account")
	parser.add_option("-i", "--inc", dest="incremental", action="store_true", default = False, help = "Use incremental backup")
	parser.add_option("-k", "--keep_status", dest="keep_read", action="store_true", default = False, help = "Keep the mail read status (Slow)")
	parser.add_option("-s", "--start", dest="start_date", action="store", help = "Backup mail starting from this date. Format: 30-Jan-2010")
	parser.add_option("-e", "--end", dest="end_date", action="store", help = "Backup mail until to this date Format: 30-Jan-2010")
	parser.add_option("--include", dest="include_labels", action="store", help = "Only backup these labels. Seperate labels by '^' Format: label1^label2")
	parser.add_option("--exclude", dest="exclude_labels", action="store", help = "Do not backup these labels. If --include is used this flag will be ignored. Seperate labels by '^' Format: label1^label2")
	parser.add_option("-c", "--config", dest="config_file", action="store", help = "Load setting from config file")
	parser.add_option("-p", "--profile", dest="profile", action="store", default = "Main", help = "Use this profile in the config file.")
	return parser

def doBackup(options, progress, overwrite = False):
	include_labels = exclude_labels = None
	if options.include_labels != None:
		include_labels = options.include_labels.split('^')
	if options.exclude_labels != None:
		exclude_labels = options.exclude_labels.split('^')
	
	backup = BackupGmail(options.username, options.password, options.backup_dir, progress)
	backup.keep_read_status = options.keep_read
	if options.incremental:
		backup.incrementalBackupTo([options.start_date, options.end_date], include_labels, exclude_labels)
	else:
		backup.backupTo([options.start_date, options.end_date], overwrite, include_labels, exclude_labels)

def doRestore(options, progress, dummy = False):
	include_labels = exclude_labels = None
	if options.include_labels != None:
		include_labels = options.include_labels.split('^')
	if options.exclude_labels != None:
		exclude_labels = options.exclude_labels.split('^')
	
	restore = RestoreGmail(options.username, options.password, options.backup_dir, progress)
	restore.restore([options.start_date, options.end_date], include_labels, exclude_labels)

if __name__ == '__main__':
	parser = getOptionParser()
	(options, args) = parser.parse_args()

	if len(args) < 3 and options.config_file == None:
		parser.print_help()
		exit()

	if options.config_file != None:
		options = loadConfigFile(options, options.config_file)[options.profile]
	else:
		options.backup_dir= args[0]
		options.username = args[1]
		options.password = args[2]
	try:
		if options.restore == True:
			doRestore(options, TerminalProgress())
		else:
			doBackup(options, TerminalProgress())
	except Exception as e:
		traceback.print_exc(e)
		exit()
