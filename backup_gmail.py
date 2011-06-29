#!/usr/bin/python

"""
Copyright 2011, Joseph Wen
"""

#TODO: MailBox

import imaplib
import traceback
import email.message, email.utils
import re, sys, hashlib, os, shutil, time, optparse, mailbox, copy
import locale
from datetime import datetime
import ConfigParser

KC_SERVICE_TEMPLATE = 'backup_gmail (%s)'

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

	class ApplicationError(Exception):
		def __init__(self, str):
			self.str = str

		def __str__(self):
			return repr(self.str)

	def __init__(self, username, password):
		self.mails = {}
		self.mboxs = {}
		self.labels = set()
		self.gmail = None
		self.username = username
		self.password = password

	def login(self):
		self.gmail_prefix = None
		self.gmail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
		try:
			ret, message = self.gmail.login(self.username, self.password)
		except Exception as e:
			raise self.AuthError("username or password incorrect")
		
	def __resultCountCheck(self, result, number):
		if number.find(':') == -1:
			return len(result) == 1
		else:
			l = number.split(':')
			return len(result) == int(l[1]) - int(l[0]) + 1

	@UIDconverter
	def fetchRFC822(self, uid):
		data = []
		while not self.__resultCountCheck(data, uid):
			ret, data = self.gmail.fetch(uid, 'RFC822')
			data = filter(lambda x: len(x) == 2, data)
			data = map(lambda x:(getUID(x[0]), x[1]), data)
		return data

	@UIDconverter
	def fetchMessageId(self, uid):
		data = []
		while not self.__resultCountCheck(data, uid):
			ret, data = self.gmail.fetch(uid, '(BODY[HEADER.FIELDS (MESSAGE-ID)])')
			data = filter(lambda x: len(x) == 2, data)
			data = map(lambda x:(getUID(x[0]), getMID(x[1])), data)
		return data

	@UIDconverter
	def fetchRFC822Info(self, uid): # return UID, SIZE, SEEN
		data = []
		while not self.__resultCountCheck(data, uid):
			ret, data = self.gmail.fetch(uid, '(RFC822.SIZE FLAGS)')
			data = map(lambda x : (getUID(x), re.findall('RFC822.SIZE ([0-9]+)', x)[0], re.search("Seen", x) != None), data)
		return data

	# start is inclusive, end is exclusive
	def searchByDate(self, start, end = None):
		if start == None and end == None:
			ret, result = self.gmail.search(None, 'ALL')
			return result[0].split()
		elif end == None:
			gstart = GmailDate.fromLocal(start)
			ret, result = self.gmail.search(None, '(SINCE "%s")' % (gstart, ))
			return result[0].split()
		elif start == None:
			gend = GmailDate.fromLocal(end)
			ret, result = self.gmail.search(None, '(BEFORE "%s")' % (gend, ))
			return result[0].split()
		else:
			gstart = GmailDate.fromLocal(start)
			gend = GmailDate.fromLocal(end)
			ret, result = self.gmail.search(None, '(SINCE "%s") (BEFORE "%s")' % (gstart, gend))
			return result[0].split()

	def fetchSpecialLabels(self):
		ret, result = self.gmail.xatom('XLIST', '', '*')
		xlist = self.gmail.response('XLIST')[1]
		xlabels = {}
		for x in xlist:
			m = re.match(r'\(([^\)]+)\) "/" "([^"]+)"', x)
			if m is None:
				continue
			attrbs = set(m.group(1).split())
			label = m.group(2)

			for k in ['Inbox', 'AllMail', 'Drafts', 'Sent', 'Starred', 'Trash' ]:
				attr = '\\' + k
				if attr in attrbs:
					xlabels[k] = label
		return xlabels

	def fetchLabelNames(self):
		labels = self.gmail.list()[1]
		return map(lambda x:x[0], 
			filter(lambda x : len(x) > 0, 
			map(lambda x : re.findall('\(\\\\HasNoChildren\) "/" "([^"]+)"', x), labels)))

	def isValidMailBox(self, name):
		ret, mail_count = self.gmail.select(name)
		return (ret != 'NO')

	def selectMailBox(self, name):
		ret, mail_count = self.gmail.select(name)
		if ret == 'NO':
			raise self.SelectMailBoxError(name, self.fetchLabelNames())
		return mail_count

	def getGmailPrefix(self):
		if self.gmail_prefix != None:
			return self.gmail_prefix
		specials = self.fetchSpecialLabels()
		allMail = specials['AllMail']    # no space
		p = allMail.split('/')[0]
		self.gmail_prefix = p
		return self.gmail_prefix

	def checkDir(self):		
		if not os.path.isdir(self.dest):
			raise ApplicationError('Error: [%s] is not a directory!\n' % (self.dest, ))

	def readLabelFile(self):
		labelFile = "%s/label" % (self.dest, )
		if os.path.exists(labelFile):
			with open(labelFile) as f:
				for line in f.readlines():
					m = MailMetaData.fromStr(line.strip())
					self.mails[m.id] = m
					for l in m.labels:
						self.labels.add(l)

	def isInTimeFrame(self, date_range, dateTuple):
		if dateTuple == None:
			return True
		if date_range == None or (date_range[0] == None and date_range[1] == None):
			return True
		try:
			date = datetime(*dateTuple[:7])
		except:
			return False
		if date_range[0] == None:
			end = datetime.strptime(date_range[1], "%d-%b-%Y")
			return date < end
		if date_range[1] == None:
			start = datetime.strptime(date_range[0], "%d-%b-%Y")
			return start < date 
		start = datetime.strptime(date_range[0], "%d-%b-%Y")
		end = datetime.strptime(date_range[1], "%d-%b-%Y")
		return start < date and date < end

	def setFlag(self, uid, flag):
		self.gmail.store(uid, '+Flags', flag)
	
	def unsetFlag(self, uid, flag):
		self.gmail.store(uid, '-Flags', flag)

class BackupGmail(Gmail):
	def __init__(self, username, password, dest, progress = None):
		super(BackupGmail, self).__init__(username, password)
		self.keep_read_status = False
		self.progress = progress
		self.dest = dest
		self.strict_exclude = False
		self.exclude_mids = set()
		self.written = {}

		self.fetchBuffer = []
		self.fetchStart = '-1'
		self.fetchEnd = '-1'
		self.fetchSize = 0

	def formatMegabytes(self, v):
		v /= 1000000.0
		return '%.2f MB' % (v,)

	def __initProgress(self, infos):
		total = sum(map(lambda x:int(x[1]), infos))
		self.progress.formatter = self.formatMegabytes
		self.progress.setRange(0, total)
		self.progress.setValue(0)

	def __fetchMailByLabel(self, label, date_range):
		self.progress.setText("Fetching %s [calculate size]" % (label, ))

		isValid = self.isValidMailBox(label)
		if isValid == False:
			self.progress.setText("Label [%s] does not exist." % (label, ))
			self.progress.newLine()
			return

		mail_count = self.selectMailBox(label)
		if date_range[0] == None and date_range[1] == None:
			infos = self.fetchRFC822Info('1:%s' % (mail_count[0], ))
			envs = self.fetchMessageId('1:%s' % (mail_count[0], ))
		else:
			date_range = self.searchByDate(*date_range)
			infos = self.fetchRFC822Info(date_range)
			envs = self.fetchMessageId(date_range)

		self.progress.setText("Fetching %s [@value/@max]" % (label, ))
		self.__initProgress(infos)
		total = 0

		for i, (env, info) in enumerate(zip(envs, infos)):
			uid, mid = env
			uid, size, seen = info
			if mid not in self.mails:
				if mid not in self.exclude_mids:
					self.__fetchMail(uid, seen, label, size)
			else:
				self.mails[mid].labels.add(label)
				if seen == False and self.keep_read_status:
					self.unsetFlag(uid, '\\Seen')
			total += int(size)
			self.progress.setValue(total)
			
		#Flush all pending request
		self.__flushFetchMailRequest()

		self.progress.setText("Fetched %s [@value/@max]" % (label, ))
		self.progress.newLine()

	def __processMail(self, rfc, seen, label):
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

		mdir = "%s/%s" % (self.dest, fold)
		if not os.path.isdir(mdir):
			os.mkdir(mdir)

		mfile = "%s/%s/%s" % (self.dest, fold, h)
		if not os.path.exists(mfile):
			with open(mfile, 'w') as f:
				try:
					f.write(rfc)			
				except:
					# in case the write fails, delete the file 
					f.close()
					os.remove(mfile)
					raise
			self.written[mid] = h

		if mid not in self.mails:
			self.mails[mid] = MailMetaData(mid, h, fold)
			self.mails[mid].seen = seen

		self.mails[mid].labels.add(label)

	def __flushFetchMailRequest(self):
		if self.fetchBuffer == []:
			return

		rfcs = self.fetchRFC822('%s:%s' % (self.fetchStart, self.fetchEnd))
		if self.keep_read_status:
			for i, rfc in enumerate(rfcs):
				if self.fetchBuffer[i][0] == False:
					self.unsetFlag(rfc[0], '\\Seen')
		for i, rfc in enumerate(rfcs):
			self.__processMail(rfc[1], *self.fetchBuffer[i])

		self.fetchBuffer = []
		self.fetchEnd = '-1'
		self.fetchSize = 0

	def __fetchMail(self, uid, seen, label, size):
		size = int(size)
		if len(self.fetchBuffer) > 300 or self.fetchSize > 10000000:
			self.__flushFetchMailRequest()
		if int(self.fetchEnd) + 1 == int(uid):
			self.fetchEnd = uid
			self.fetchBuffer += [(seen, label)]
			self.fetchSize += size
		else:
			self.__flushFetchMailRequest()
			self.fetchStart = uid
			self.fetchEnd = uid
			self.fetchBuffer += [(seen, label)]
			self.fetchSize += size

	# Fetch default Gmail folders excluding the special \Drafts and \Trash 
	def __fetchDefaultLabels(self):
		labels = self.fetchLabelNames()
		specials = self.fetchSpecialLabels()
		allMail = specials['AllMail']    # no space
		if allMail not in labels:
			labels.append(allMail)
		ignore = [ specials['Drafts'], specials['Trash'] ] 
		labels = filter(lambda x : x not in ignore , labels)
		return labels

	def __fetchByLabels(self, date_range, include_labels, exclude_labels):
		self.written = {}
		self.exclude_mids = set()
		if self.strict_exclude:
			for l in filter(lambda x : x in exclude_labels, self.fetchLabelNames()):
				mail_count = self.selectMailBox(l)
				tmp = set(map(lambda x:x[1], self.fetchMessageId("1:%s" % (mail_count[0], ))))
				self.exclude_mids.update(tmp)
		
		for l in set(include_labels).difference(set(exclude_labels)):
			self.__fetchMailByLabel(l, date_range)
			
		self.progress.setText("Backed up %d physical message(s)." % (len(self.written), ))
		self.progress.newLine()
	
	def __outputLable(self):
		with open(self.dest + '/label', 'w') as f:
			for k in self.mails:
				print >> f, self.mails[k]

	def makeDir(self):
		if not os.path.exists(self.dest):
			os.mkdir(self.dest)
		self.checkDir()

	def backupTo(self, date_range = None, include_labels = None, exclude_labels = []):
		self.login()
		self.makeDir()
		self.readLabelFile()

		try:
			if include_labels == None:
				include_labels = self.__fetchDefaultLabels()
			if exclude_labels == None:
				exclude_labels = []
			self.__fetchByLabels(date_range, include_labels, exclude_labels)
		finally:
			self.__outputLable()

class SaveMbox(Gmail):
	def __init__(self, src, mbox_export, progress):
		super(SaveMbox, self).__init__(None, None)
		self.progress = progress
		self.dest = src
		self.mbox_export = mbox_export

	def __addToMBox(self, label, mail):
		if label not in self.mboxs:
			odir = os.path.expanduser(self.mbox_export)
			self.mboxs[label] = mailbox.mbox('%s/%s.mbox' % (odir, label.replace('/', '-'), ), create = True)
			self.mboxs[label].clear()
			self.mboxs[label].flush()
		self.mboxs[label].add(mail)

	def save(self, date_range = None, include_labels = None, exclude_labels = None):
		self.checkDir()
		self.readLabelFile()

		odir = os.path.expanduser(self.mbox_export)
		if not os.path.exists(odir):
			os.mkdir(odir)

		ntotal = len(self.mails)
		self.progress.setText("Processing messages to mbox(es) [@value/@max]")
		self.progress.setRange(0, ntotal)

		nsaved = 0
		for i, m in enumerate(self.mails.values()):
			self.progress.setValue(i + 1)
			include = m.labels.intersection(include_labels) if include_labels != None else m.labels
			exclude = m.labels.intersection(exclude_labels) if exclude_labels != None else set()
			if include_labels != None and include == set():
				continue
			if exclude_labels != None and exclude != set():
				continue
			with open("%s/%s/%s" % (self.dest, m.folder, m.hash_value)) as f:
				mail = f.read()
				e = email.message_from_string(mail)
				if date_range is not None:
					dateTuple = email.utils.parsedate(e.get('date'))
					if not self.isInTimeFrame(date_range, dateTuple):
						continue
					
				updateLabel = m.labels.difference(exclude).intersection(include)
				for label in updateLabel:
					self.__addToMBox(label, mail)
				nsaved += 1

		for i, m in enumerate(self.mboxs.values()):
			m.flush()

		self.progress.setText("Saved %d of %d message(s) to mbox(es)" % (nsaved, ntotal))
		self.progress.newLine()
		
class RestoreGmail(Gmail):
	def __init__(self, username, password, src, progress):
		super(RestoreGmail, self).__init__(username, password)
		self.progress = progress
		self.dest = src

	def __appendMessage(self, message, date, mailbox = None):
		ret, msg = self.gmail.append(mailbox, None, date, message)
		return re.findall("APPENDUID [0-9]+ ([0-9]+)", msg[0])[0]

	def __assignLabel(self, uid, label):
		if label not in self.labels:
			self.gmail.create(label)
			self.labels = set(self.fetchLabelNames())
		ret, msg = self.gmail.uid('COPY', uid, label)
	
	def restore(self, date_range = None, include_labels = None, exclude_labels = None):
		self.checkDir()
		self.login()

		# Read label file for messages, but then set self.labels to what
		# exists on the server. Each message in self.mails will still have 
		# its private set of labels
		self.readLabelFile()
		self.labels = set(self.fetchLabelNames())

		ntotal = len(self.mails)
		self.progress.setText("Processing messages for restore [@value/@max]")
		self.progress.setRange(0, ntotal)
		
		specials = self.fetchSpecialLabels()
		allMail = specials['AllMail']    # no space

		nrestored = 0
		mail_count = self.selectMailBox('INBOX')
		for i, m in enumerate(self.mails.values()):
			self.progress.setValue(i + 1)
			include = m.labels.intersection(include_labels) if include_labels != None else m.labels
			exclude = m.labels.intersection(exclude_labels) if exclude_labels != None else set()
			if include_labels != None and include == set():
				continue
			if exclude_labels != None and exclude != set():
				continue
			with open("%s/%s/%s" % (self.dest, m.folder, m.hash_value)) as f:
				mail = f.read()
				e = email.message_from_string(mail)
				dateTuple = email.utils.parsedate(e.get('date'))
				if date_range is not None:
					if not self.isInTimeFrame(date_range, dateTuple):
						continue
				uid = self.__appendMessage(mail, dateTuple, 'INBOX')
				nrestored += 1
				updateLabel = m.labels.difference(exclude).intersection(include)
				for label in updateLabel:
					if label != allMail:
						self.__assignLabel(uid, label)

		self.progress.setText("Restored %d of %d message(s)." % (nrestored, ntotal))
		self.progress.newLine()
	
class TerminalProgress:
	def __init__(self):
		self.value = 0
		self.min = 0
		self.max = 0
		self.maxWidth = 0
		self.formatter = self.justString

	def justString(self, v):
		return str(v)

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
		x = x.replace('@value', self.formatter(self.value))
		x = x.replace('@max', self.formatter(self.max))
		xlen = len(x)
		if xlen < self.maxWidth:
			x = x + ' ' * (self.maxWidth - xlen)
		else:
			self.maxWidth = xlen
		print '\r%s\r' % (x, ),
		sys.stdout.flush()
		
	def newLine(self):
		self.maxWidth = 0
		print 

class GmailDate:
	GMAIL_DFMT = '%d-%b-%Y'  # i.e., dd-MMM-yyyy
	GMAIL_LOC = 'en_US'

	@classmethod
	def toLocal(cls, gmail_date, format=GMAIL_DFMT):
		currlang, encoding = locale.getlocale(locale.LC_TIME)
		locale.setlocale(locale.LC_TIME, cls.GMAIL_LOC) 
		try:
			d = datetime.strptime(gmail_date, cls.GMAIL_DFMT)
		finally:
			locale.setlocale(locale.LC_TIME, currlang)
		return d.strftime(format)

	@classmethod
	def fromLocal(cls, date_string, format=GMAIL_DFMT):
		d = datetime.strptime(date_string, format)
		currlang, encoding = locale.getlocale(locale.LC_TIME)
		locale.setlocale(locale.LC_TIME, cls.GMAIL_LOC) 
		try:
			return d.strftime(cls.GMAIL_DFMT)
		finally:
			locale.setlocale(locale.LC_TIME, currlang)

class KeyringUtil:
	def __init__(self, service_template):
		self.service_template = service_template
		try:
			import keyring
		except ImportError:
			self.get_password_function = self.__noop_get_password
			self.set_password_function = self.__noop_set_password
		else:
			self.get_password_function = keyring.get_password
			self.set_password_function = keyring.set_password

	def get_password(self, username):
		servicename = self.service_template % (username, )
		return self.get_password_function(servicename, username)

	def set_password(self, username, password):
		servicename = self.service_template % (username, )
		self.set_password_function(servicename, username, password)

	def __noop_get_password(self, servicename, username):
		return None

	def __noop_set_password(self, servicename, username, password):
		return

def loadConfigFile(options, filename):
	config = ConfigParser.SafeConfigParser()
	config.read([filename, os.path.expanduser('~/.backup_gmail.cfg')])
	keyu = KeyringUtil(KC_SERVICE_TEMPLATE)
	result = {}
	for section in config.sections():
		rsec = result[section] = copy.copy(options)
		rsec.username = config.get(section, 'username')
		rsec.backup_dir = config.get(section, 'backup_dir')
		if config.has_option(section, 'keep_read'):
			rsec.keep_read = config.getboolean(section, 'keep_read')
		if config.has_option(section, 'start_date'):
			rsec.start_date = config.get(section, 'start_date')
		if config.has_option(section, 'end_date'):
			rsec.end_date = config.get(section, 'end_date')
		if config.has_option(section, 'include_labels'):
			rsec.include_labels = config.get(section, 'include_labels')
		if config.has_option(section, 'exclude_labels'):
			rsec.exclude_labels = config.get(section, 'exclude_labels')
		if config.has_option(section, 'mbox_export'):
			rsec.mbox_export = config.get(section, 'mbox_export')
		if config.has_option(section, 'strict_exclude'):
			rsec.strict_exclude = config.getboolean(section, 'strict_exclude')
		if rsec.username is not None and len(rsec.username):
			rsec.password = keyu.get_password(rsec.username)
	return result

def saveConfigFile(profiles, filename):
	def set_helper(cfg, section, option, value):
		if value == None:
			return
		return cfg.set(section, option, str(value))
	keyu = KeyringUtil(KC_SERVICE_TEMPLATE)
	config = ConfigParser.SafeConfigParser()
	for section in profiles:
		p = profiles[section]
		config.add_section(section)
		set_helper(config, section, 'username', p.username)
		set_helper(config, section, 'backup_dir', p.backup_dir)
		set_helper(config, section, 'keep_read', p.keep_read)
		set_helper(config, section, 'start_date', p.start_date)
		set_helper(config, section, 'end_date', p.end_date)
		set_helper(config, section, 'include_labels', p.include_labels)
		set_helper(config, section, 'exclude_labels', p.exclude_labels)
		set_helper(config, section, 'mbox_export', p.mbox_export)
		set_helper(config, section, 'strict_exclude', p.strict_exclude)
		if p.password is not None and len(p.password):
			if p.username is not None and len(p.username):
				keyu.set_password(p.username, p.password)
	with open(filename, 'w') as f:
		config.write(f)

def getOptionParser():
	parser = optparse.OptionParser(usage = "%prog [options] [backup_dir email@address password]")
	parser.add_option("--dest", dest="backup_dir", action="store", help="Backup destination")
	parser.add_option("--user", dest="username", action="store", help = "Gmail email@address")
	parser.add_option("--password", dest="password", action="store", help = "Gmail password")
	parser.add_option("-P", "--prompt", dest="prompt", action="store_true", default = False, help = "Prompt for Gmail credentials")
	parser.add_option("-r", "--restore", dest="restore", action="store_true", default = False, help = "Restore backup to online gmail account")
	parser.add_option("-m", "--mbox_export", dest="mbox_export", action="store", help = "Save mbox(es) to directory")
	parser.add_option("-k", "--keep_status", dest="keep_read", action="store_true", default = False, help = "Keep the mail read status (Slow)")
	parser.add_option("-s", "--start", dest="start_date", action="store", help = "Backup mail starting from this date (inclusive SINCE). Format: dd-MMM-yyyy")
	parser.add_option("-e", "--end", dest="end_date", action="store", help = "Backup mail until to this date (exclusive BEFORE). Format: dd-MMM-yyyy")
	parser.add_option("--include", dest="include_labels", action="store", help = "Only backup these labels. Seperate labels by '^' Format: label1^label2")
	parser.add_option("--exclude", dest="exclude_labels", action="store", help = "Do not backup these labels. Seperate labels by '^' Format: label1^label2")
	parser.add_option("--strict_exclude", dest="strict_exclude", action="store_true", default = False, help = "Exclude messages also by message-id ")
	parser.add_option("-c", "--config", dest="config_file", action="store", help = "Load setting from config file")
	parser.add_option("-p", "--profile", dest="profile", action="store", default = "Main", help = "Use this profile in the config file.")
	return parser

def doBackup(options, progress):
	include_labels = exclude_labels = None
	if options.include_labels != None:
		include_labels = options.include_labels.split('^')
	if options.exclude_labels != None:
		exclude_labels = options.exclude_labels.split('^')
	
	backup = BackupGmail(options.username, options.password, options.backup_dir, progress)
	backup.strict_exclude = options.strict_exclude
	backup.keep_read_status = options.keep_read
	backup.backupTo([options.start_date, options.end_date], include_labels, exclude_labels)

def doRestore(options, progress):
	include_labels = exclude_labels = None
	if options.include_labels != None:
		include_labels = options.include_labels.split('^')
	if options.exclude_labels != None:
		exclude_labels = options.exclude_labels.split('^')
	
	restore = RestoreGmail(options.username, options.password, options.backup_dir, progress)
	restore.restore([options.start_date, options.end_date], include_labels, exclude_labels)

def doMbox(options, progress):
	include_labels = exclude_labels = None
	if options.include_labels != None:
		include_labels = options.include_labels.split('^')
	if options.exclude_labels != None:
		exclude_labels = options.exclude_labels.split('^')
	
	savem = SaveMbox(options.backup_dir, options.mbox_export, progress)
	savem.save([options.start_date, options.end_date], include_labels, exclude_labels)

if __name__ == '__main__':
	parser = getOptionParser()
	(options, args) = parser.parse_args()
	
	if options.config_file != None:
		options = loadConfigFile(options, options.config_file)[options.profile]

	if len(args) >= 1:
		options.backup_dir = args[0]
	elif options.backup_dir is None:
		parser.print_help()
		exit()

	if len(args) >= 2:
		options.username = args[1]
	if len(args) >= 3:
		options.password = args[2]

	if options.prompt:
		import getpass
		options.username = raw_input('Username: ')
		options.password = getpass.getpass()
		
	canConnect = (options.username is not None and options.password is not None)
	if options.mbox_export is None and canConnect == False:
		parser.print_help()
		exit()
		
	try:
		if canConnect == False:
			pass
		elif options.restore == True:
			doRestore(options, TerminalProgress())
		else:
			doBackup(options, TerminalProgress())
			
		if options.mbox_export is not None:
			doMbox(options, TerminalProgress())
	except Exception as e:
		traceback.print_exc(e)
		exit()
