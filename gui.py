#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Copyright 2011, Joseph Wen
"""
 
import sys
import traceback
from PySide.QtCore import *
from PySide.QtGui import *

import backup_gmail

def getGuiOptionParser():
	parser = backup_gmail.getOptionParser()
	parser.add_option("--user", dest="username", action="store", help = "Gmail account name")
	parser.add_option("--password", dest="password", action="store", help = "Gmail account password")
	parser.add_option("--dest", dest="backup_dir", action="store", help = "Backup destination")
	return parser
 
class MainWindow(QMainWindow):
	def __init__(self, parent=None):
		super(MainWindow, self).__init__(parent)
		self.setWindowTitle("Backup Gmail")

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

		self.keep_read = QCheckBox("Keep read/unread (Slow)")
		self.inc = QCheckBox("Incremental Backup")

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

		self.label_filter_label = QLabel("Label Filter:")
		self.include_label = QRadioButton("Include")
		self.include_label.setChecked(True)
		self.exclude_label = QRadioButton("Exclude")
		self.label_filter_text = QLineEdit()
		self.label_filter_text.setPlaceholderText("Keep empty to fetch all labels")

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
		layout.addLayout(vTmp, 5, 2)

		layout.addWidget(self.backup_label, 6, 0)
		layout.addWidget(self.backup_path, 6, 1)
		layout.addWidget(self.backup_path_btn, 6, 2)


		btnLayout = QHBoxLayout()
		btnLayout.addWidget(self.load_config_btn)
		btnLayout.addWidget(self.store_config_btn)
		btnLayout.addWidget(self.restore_btn)
		btnLayout.addWidget(self.backup_btn)
		
		checkLayout = QHBoxLayout()
		checkLayout.addWidget(self.keep_read)
		checkLayout.addWidget(self.inc)

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
		self.user_text.setText(options.username)
		self.pass_text.setText(options.password)
		self.backup_path.setText(options.backup_dir)

		self.keep_read.setChecked(options.keep_read == True)
		self.inc.setChecked(options.incremental == True)

		if options.start_date != None:
			self.start_date_enable.setChecked(True)
			self.start_date.setDate(QDate.fromString(options.start_date, "dd-MMM-yyyy"))
		else:
			self.start_date_enable.setChecked(False)
		
		if options.end_date != None:
			self.end_date_enable.setChecked(True)
			self.end_date.setDate(QDate.fromString(options.end_date, "dd-MMM-yyyy"))
		else:
			self.end_date_enable.setChecked(False)

		if options.include_labels != None:
			self.include_label.setChecked(True)
			self.label_filter_text.setText(options.include_labels)
		elif options.exclude_labels != None:
			self.exclude_label.setChecked(True)
			self.label_filter_text.setText(options.exclude_labels)
		else:
			self.label_filter_text.setText("")

	def saveUI(self, options):
		options.username = self.user_text.text()
		options.password = self.pass_text.text()
		options.backup_dir = self.backup_path.text()
		options.keep_read = self.keep_read.isChecked()
		options.incremental = self.inc.isChecked()
		if self.start_date_enable.isChecked():
			options.start_date = self.start_date.date().toString("dd-MMM-yyyy")
		else:
			options.start_date = None
		
		if self.end_date_enable.isChecked():
			options.end_date = self.end_date.date().toString("dd-MMM-yyyy")
		else:
			options.end_date = None
		
		if self.label_filter_text.text() != '':
			if self.include_label.isChecked():
				options.include_labels = self.label_filter_text.text()
			else:
				options.exclude_labels = self.label_filter_text.text()
		else:
			options.include_labels = None
			options.exclude_labels = None

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
			self.setUI(result[self.config_select.itemText(0)])
			self.config_file = result

	def backup(self):
		self.saveUI(self.config_file[self.current_profile])
		if self.config_file[self.current_profile].backup_dir == '':
			self.show_error("Backup Dir can not be empty")
			return

		self.restore_btn.setDisabled(True)
		self.backup_btn.setDisabled(True)
		
		self.t = BackupRestoreThread(backup_gmail.doBackup, self.config_file[self.current_profile])
		self.t.finished.connect(self.backup_restore_finished)
		self.t.error.connect(self.show_error)
		self.t.backup_success.connect(self.show_backup_success)
		self.t.start()
		self.timer = QTimer(self)
		self.timer.timeout.connect(self.update_progress)
		self.timer.start(1000)

		self.progress = QProgressDialog(self)
		self.progress.setAutoClose(False)
		self.progress.setWindowModality(Qt.WindowModal)
		self.progress.setWindowTitle("Backup from %s" % (self.user_text.text(), ))
		self.progress.setLabelText(" " * 100)
		self.progress.show()
	
	def restore(self):
		self.restore_btn.setDisabled(True)
		self.backup_btn.setDisabled(True)
		self.saveUI(self.config_file[self.current_profile])
		self.t = BackupRestoreThread(backup_gmail.doRestore, self.config_file[self.current_profile])
		self.t.finished.connect(self.backup_restore_finished)
		self.t.error.connect(self.show_error)
		self.t.backup_success.connect(self.show_restore_success)
		self.t.start()
		self.timer = QTimer(self)
		self.timer.timeout.connect(self.update_progress)
		self.timer.start(1000)

		self.progress = QProgressDialog(self)
		self.progress.setAutoClose(False)
		self.progress.setWindowModality(Qt.WindowModal)
		self.progress.setWindowTitle("Restore to %s" % (self.user_text.text(), ))
		self.progress.setLabelText(" " * 100)
		self.progress.show()

	def show_error(self, message):
		msgBox = QMessageBox()
		msgBox.setWindowTitle("Error")
		msgBox.setIcon(QMessageBox.Critical)
		msgBox.setText(message)
		msgBox.exec_()
	
	def show_password_error(self):
		msgBox = QMessageBox()
		msgBox.setWindowTitle("Error")
		msgBox.setIcon(QMessageBox.Critical)
		msgBox.setText("username or password incorrect")
		msgBox.exec_()
	
	def show_backup_success(self):
		msgBox = QMessageBox()
		msgBox.setWindowTitle("Success")
		msgBox.setIcon(QMessageBox.Information)
		msgBox.setText("Backup success")
		msgBox.exec_()
	
	def show_restore_success(self):
		msgBox = QMessageBox()
		msgBox.setWindowTitle("Success")
		msgBox.setIcon(QMessageBox.Information)
		msgBox.setText("Restore success")
		msgBox.exec_()

	def backup_restore_finished(self):
		self.restore_btn.setDisabled(False)
		self.backup_btn.setDisabled(False)

		self.progress.close()

	def update_progress(self):
		self.progress.setRange(self.t.prog.min, self.t.prog.max)
		self.progress.setValue(self.t.prog.value)
		self.progress.setLabelText(self.t.prog.getText())

class GuiProgress:
	def __init__(self):
		self.min = 0
		self.max = 1000
		self.value = 0
		self.text = ""

	def setRange(self, a, b):
		self.min = a
		self.max = b / 1000.0

	def setValue(self, value):
		self.value = value / 1000.0

	def setText(self, text):
		self.text = text

	def getText(self):
		tmp = self.text.replace("@max", str(self.max))
		tmp = tmp.replace("@min", str(self.min))
		tmp = tmp.replace("@value", str(self.value))
		return tmp

class BackupRestoreThread(QThread):
	error = Signal(str)
	backup_success = Signal()
	def __init__(self, func, options, parent=None):
		super(BackupRestoreThread, self).__init__(parent)
		self.func = func
		self.options = options
		self.prog = GuiProgress()

	def run(self):
		try:
			self.func(self.options, self.prog, True)
		except Exception as e:
			traceback.print_exc(e)
			self.error.emit(e.__str__())
			return
		self.backup_success.emit()

if __name__ == '__main__':
	app = QApplication(sys.argv)
	main = MainWindow()
	main.show()
	sys.exit(app.exec_())
