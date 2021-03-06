#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Copyright 2011, Joseph Wen
"""
 
import sys
import locale
import traceback
from datetime import datetime, date
from PySide.QtCore import *
from PySide.QtGui import *

import backup_gmail

def getGuiOptionParser():
	parser = backup_gmail.getOptionParser()
	return parser
 
class MainWindow(QMainWindow):
	def __init__(self, parent=None):
		super(MainWindow, self).__init__(parent)
		self.setWindowTitle("Backup Gmail")
		self.setMinimumSize(640, 0)

		self.config_label = QLabel("Profile:")
		self.config_select = QComboBox()
		self.config_select.addItem("Main")
		self.config_select.currentIndexChanged.connect(self.updateUI)
		self.config_add_btn = QPushButton("Add Profile")
		self.config_add_btn.clicked.connect(self.addProfile)
		(options, args) = getGuiOptionParser().parse_args()
		self.config_file = {'Main' : options}
		self.current_profile = 'Main'

		self.user_label = QLabel("Username:")
		self.user_text  = QLineEdit()
		self.pass_label = QLabel("Password:")
		self.pass_text  = QLineEdit()
		self.pass_text.setEchoMode(QLineEdit.Password)

		self.backup_label = QLabel("Backup dir:")
		self.backup_path = QLineEdit()
		self.backup_path_btn = QPushButton("Select")

		self.keep_read = QCheckBox("Keep the mail read status")
		self.keep_read.setChecked(True)

		self.start_date_label = QLabel("From:")
		self.start_date = QDateEdit()
		self.start_date.setDisplayFormat("dd-MMM-yyyy")
		self.start_date.setDate(QDate.currentDate())
		self.start_date.setDisabled(True)
		self.start_date_enable = QCheckBox("Enable")
		self.start_date_enable.stateChanged.connect(self.start_date.setEnabled)
		
		self.end_date_label = QLabel("To:")
		self.end_date = QDateEdit()
		self.end_date.setDisplayFormat("dd-MMM-yyyy")
		self.end_date.setDisabled(True)
		self.end_date.setDate(QDate.currentDate())
		self.end_date_enable = QCheckBox("Enable")
		self.end_date_enable.stateChanged.connect(self.end_date.setEnabled)

		self.label_filter_label = QLabel("Label(s) Filter:")
		self.include_label = QRadioButton("Include")
		self.include_label.setChecked(True)
		self.exclude_label = QRadioButton("Exclude")
		self.strict_exclude = QRadioButton("Exclude (Strict)")
		self.label_filter_text = QLineEdit()
		self.label_filter_text.setPlaceholderText("Optional; separate by '^'")
		
		self.label_regex_label = QLabel("Label Regex:")
		self.label_regex_text = QLineEdit()
		self.label_regex_text.setPlaceholderText("Optional")

		self.label_target_label = QLabel("Restore also to:")
		self.label_target_text = QLineEdit()
		self.label_target_text.setPlaceholderText("Optional label")

		self.load_config_btn = QPushButton("Load Config")        
		self.store_config_btn = QPushButton("Save Config")        
		self.restore_btn = QPushButton("Restore")        
		self.backup_btn = QPushButton("Backup")        

		# Create layout and add widgets
		vLayout = QVBoxLayout()
		layout = QGridLayout()

		layout.addWidget(self.config_label, 0, 0)
		layout.addWidget(self.config_select, 0, 1)
		layout.addWidget(self.config_add_btn, 0, 2)

		layout.addWidget(self.user_label, 1, 0)
		layout.addWidget(self.user_text, 1, 1)
		layout.addWidget(self.pass_label, 2, 0)
		layout.addWidget(self.pass_text, 2, 1)

		layout.addWidget(self.start_date_label, 3, 0)
		layout.addWidget(self.start_date, 3, 1)
		layout.addWidget(self.start_date_enable, 3, 2)
		layout.addWidget(self.end_date_label, 4, 0)
		layout.addWidget(self.end_date, 4, 1)
		layout.addWidget(self.end_date_enable, 4, 2)
		
		layout.addWidget(self.label_filter_label, 5, 0)
		layout.addWidget(self.label_filter_text, 5, 1)
		vTmp = QVBoxLayout()
		vTmp.addWidget(self.include_label)
		vTmp.addWidget(self.exclude_label)
		vTmp.addWidget(self.strict_exclude)
		layout.addLayout(vTmp, 5, 2)
		
		layout.addWidget(self.label_regex_label, 6, 0)
		layout.addWidget(self.label_regex_text, 6, 1)

		layout.addWidget(self.backup_label, 7, 0)
		layout.addWidget(self.backup_path, 7, 1)
		layout.addWidget(self.backup_path_btn, 7, 2)

		layout.addWidget(self.label_target_label, 8, 0)
		layout.addWidget(self.label_target_text, 8, 1)

		btnLayout = QHBoxLayout()
		btnLayout.addWidget(self.load_config_btn)
		btnLayout.addWidget(self.store_config_btn)
		btnLayout.addWidget(self.restore_btn)
		btnLayout.addWidget(self.backup_btn)
		
		checkLayout = QHBoxLayout()
		checkLayout.addWidget(self.keep_read)

		vLayout.addLayout(layout)
		vLayout.addLayout(checkLayout)
		vLayout.addLayout(btnLayout)
		self.vLayout = vLayout

		# Set dialog layout
		centralwidget = QWidget(self)
		centralwidget.setLayout(vLayout)
		self.setCentralWidget(centralwidget)

		self.load_config_btn.clicked.connect(self.loadConfig)
		self.store_config_btn.clicked.connect(self.storeConfig)
		self.backup_btn.clicked.connect(self.backup)
		self.restore_btn.clicked.connect(self.restore)
		self.backup_path_btn.clicked.connect(self.getDir)
	
	def getDir(self):
		name = QFileDialog.getExistingDirectory()
		if name != '':
			self.backup_path.setText(name)
	
	def addProfile(self):
		text, ok = QInputDialog.getText(self, "Create Profile", "Profile Name:", QLineEdit.Normal)
		if ok == True and text != '':
			if text in self.config_file:
				msgBox = QMessageBox()
				msgBox.setWindowTitle("Error")
				msgBox.setIcon(QMessageBox.Critical)
				msgBox.setText("Profile [%s] already exist." % (text, ))
				msgBox.exec_()
				return
			(options, args) = getGuiOptionParser().parse_args()
			self.config_file[text] = options
			self.config_select.addItem(text)
			self.config_select.setCurrentIndex(self.config_select.count() - 1)
	
	def updateUI(self, text):
		if text in self.config_file:
			self.saveUI(self.config_file[self.current_profile])
			self.setUI(self.config_file[text])
			self.current_profile = text

	def setUI(self, options):
		if options.username is not None:
			self.user_text.setText(options.username.decode('utf-8'))
		else:
			self.user_text.clear()
		if options.password is not None:
			self.pass_text.setText(options.password.decode('utf-8'))
		else:
			self.pass_text.clear()
		if options.backup_dir is not None:
			self.backup_path.setText(options.backup_dir.decode('utf-8'))
		else:
			self.backup_path.clear()

		self.keep_read.setChecked(options.keep_read == True)

		if options.start_date != None:
			sdate = QDate.fromString(options.start_date.decode('utf-8'), "dd-MMM-yyyy")
			self.start_date_enable.setChecked(True)
			self.start_date.setDate(sdate)
		else:
			self.start_date_enable.setChecked(False)
		
		if options.end_date != None:
			# options.end_date is exclusive, but UI is inclusive, so subtract 1 day
			edate = QDate.fromString(options.end_date.decode('utf-8'), "dd-MMM-yyyy").addDays(-1)
			self.end_date_enable.setChecked(True)
			self.end_date.setDate(edate)
		else:
			self.end_date_enable.setChecked(False)

		if options.include_labels != None:
			self.include_label.setChecked(True)
			self.label_filter_text.setText(options.include_labels.decode('utf-8'))
		elif options.exclude_labels != None:
		  if options.strict_exclude:
		    self.strict_exclude.setChecked(True)
		  else:
			  self.exclude_label.setChecked(True)
		  self.label_filter_text.setText(options.exclude_labels.decode('utf-8'))
		else:
			self.label_filter_text.setText("")
			
		if options.match_regex is not None:
			self.label_regex_text.setText(options.match_regex.decode('utf-8'))
		else:
			self.label_regex_text.setText("")

	def saveUI(self, options):
		options.username = self.user_text.text().encode('utf-8')
		options.password = self.pass_text.text().encode('utf-8')
		options.backup_dir = self.backup_path.text().encode('utf-8')
		options.keep_read = self.keep_read.isChecked()

		if self.start_date_enable.isChecked():
			options.start_date = self.start_date.date().toString("dd-MMM-yyyy").encode('utf-8')
		else:
			options.start_date = None
		
		if self.end_date_enable.isChecked():
			# options.end_date is exclusive, so add 1 day
			options.end_date = self.end_date.date().addDays(1).toString("dd-MMM-yyyy").encode('utf-8')
		else:
			options.end_date = None
		
		options.include_labels = None
		options.exclude_labels = None
		if self.label_filter_text.text() != '':
			if self.include_label.isChecked():
				options.include_labels = self.label_filter_text.text().encode('utf-8')
			else:
				options.exclude_labels = self.label_filter_text.text().encode('utf-8')
				options.strict_exclude = self.strict_exclude.isChecked()
		
		options.match_regex = None
		if self.label_regex_text.text() != '':
			options.match_regex = self.label_regex_text.text().encode('utf-8')

		options.label_target = None
		if self.label_target_text.text() != '':
			options.label_target = self.label_target_text.text().encode('utf-8')

	def storeConfig(self):
		name = QFileDialog.getSaveFileName(self, "Open File", ".", "Config (*.cfg)")
		name = name[0]
		if name != '':
			if name[-4:] != '.cfg':
				name += '.cfg'
			print name
			self.saveUI(self.config_file[self.current_profile])
			backup_gmail.saveConfigFile(self.config_file, name)

	def loadConfig(self):
		name = QFileDialog.getOpenFileName(self, "Open File", ".", "Config (*.cfg)")
		name = name[0]
		if name != '':
			(options, args) = getGuiOptionParser().parse_args()
			result = backup_gmail.loadConfigFile(options, name)

			self.config_select.clear()
			for section in result:
				self.config_select.addItem(section)
			self.current_profile = self.config_select.itemText(0)
			self.setUI(result[self.current_profile])
			self.config_file = result

	def backup(self):
		self.saveUI(self.config_file[self.current_profile])
		if self.config_file[self.current_profile].backup_dir == '':
			self.show_error("Backup Dir can not be empty")
			return

		self.restore_btn.setDisabled(True)
		self.backup_btn.setDisabled(True)
		
		self.progress = QProgressDialog(self)
		self.progress.setAutoClose(False)
		self.progress.setWindowModality(Qt.WindowModal)
		self.progress.setWindowTitle("Backup from %s" % (self.user_text.text(), ))
		self.progress.setLabelText(" " * 100)
		self.progress.canceled.connect(self.cancel_operation)

		self.t = BackupRestoreThread(self.getBackerup, self.config_file[self.current_profile])
		self.t.finished.connect(self.backup_restore_finished)
		self.t.error.connect(self.show_error)
		self.t.backup_success.connect(self.show_backup_success)

		self.timer = QTimer(self)
		self.timer.timeout.connect(self.update_progress)

		self.t.start()
		self.timer.start(1000)
		self.progress.show()
	
	def getBackerup(self, options, progress):
		return backup_gmail.BackupGmail(options, progress)
	
	def restore(self):
		self.restore_btn.setDisabled(True)
		self.backup_btn.setDisabled(True)
		self.saveUI(self.config_file[self.current_profile])

		self.progress = QProgressDialog(self)
		self.progress.setAutoClose(False)
		self.progress.setWindowModality(Qt.WindowModal)
		self.progress.setWindowTitle("Restore to %s" % (self.user_text.text(), ))
		self.progress.setLabelText(" " * 100)
		self.progress.canceled.connect(self.cancel_operation)

		self.t = BackupRestoreThread(self.getRestorer, self.config_file[self.current_profile])
		self.t.finished.connect(self.backup_restore_finished)
		self.t.error.connect(self.show_error)
		self.t.backup_success.connect(self.show_restore_success)

		self.timer = QTimer(self)
		self.timer.timeout.connect(self.update_progress)

		self.t.start()
		self.timer.start(1000)
		self.progress.show()
		
	def getRestorer(self, options, progress):
		return backup_gmail.RestoreGmail(options, progress)
		
	def cancel_operation(self):
		if self.t.gobj is not None:
			self.t.gobj.cancel()

	def show_error(self, message):
		msgBox = QMessageBox()
		msgBox.setText("An error has occurred.")
		msgBox.setIcon(QMessageBox.Critical)
		msgBox.setInformativeText(message)
		msgBox.exec_()
	
	def show_backup_success(self, progress):
		msgBox = QMessageBox()
		msgBox.setText("The backup finished with no errors.")
		msgBox.setIcon(QMessageBox.Information)
		msgBox.setInformativeText(progress)
		msgBox.exec_()
	
	def show_restore_success(self, progress):
		msgBox = QMessageBox()
		msgBox.setText("The restore finished with no errors.")
		msgBox.setIcon(QMessageBox.Information)
		msgBox.setInformativeText(progress)
		msgBox.exec_()

	def backup_restore_finished(self):
		self.restore_btn.setDisabled(False)
		self.backup_btn.setDisabled(False)
		self.progress.close()

	def update_progress(self):
		self.progress.setRange(self.t.prog.min, self.t.prog.max)
		self.progress.setValue(self.t.prog.value)
		self.progress.setLabelText(self.t.prog.getText().decode('utf-8'))

class GuiProgress:
	def __init__(self):
		self.min = 0
		self.max = 1000
		self.value = 0
		self.text = ""
		self.lines = []
		self.formatter = self.justString

	def setRange(self, a, b, v):
		self.min = a
		self.max = b
		if v is not None:
			self.value = v

	def setValue(self, value):
		self.value = value

	def setText(self, text):
		self.text = text

	def newLine(self):
		self.lines.append(self.getText())
		return

	def getLines(self):
		return self.lines

	def justString(self, value):
		return str(value)

	def getText(self):
		tmp = self.text.replace("@max", self.formatter(self.max))
		tmp = tmp.replace("@min", self.formatter(self.min))
		tmp = tmp.replace("@value", self.formatter(self.value))
		return tmp

class BackupRestoreThread(QThread):
	error = Signal(str)
	backup_success = Signal(str)
	def __init__(self, func, options, parent=None):
		super(BackupRestoreThread, self).__init__(parent)
		self.func = func
		self.options = options
		self.prog = GuiProgress()
		self.gobj = None

	def run(self):
		try:
			self.gobj = self.func(self.options, self.prog)
			self.gobj.execute()
		except Exception as e:
			traceback.print_exc(e)
			self.error.emit(e.__str__())
			return
		self.backup_success.emit('\n'.join(self.prog.getLines()).decode('utf-8'))

if __name__ == '__main__':
	locale.setlocale(locale.LC_TIME, '')
	app = QApplication(sys.argv)
	main = MainWindow()
	main.show()
	sys.exit(app.exec_())
