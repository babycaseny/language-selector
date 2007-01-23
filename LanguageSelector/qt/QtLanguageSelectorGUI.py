# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'QtLanguageSelectorGUI.ui'
#
# Created: Tue Jan 23 15:54:15 2007
#      by: PyQt4 UI code generator 4.0.1
#
# WARNING! All changes made in this file will be lost!

import sys
from PyQt4 import QtCore, QtGui

class Ui_QtLanguageSelectorGUI(object):
    def setupUi(self, QtLanguageSelectorGUI):
        QtLanguageSelectorGUI.setObjectName("QtLanguageSelectorGUI")
        QtLanguageSelectorGUI.resize(QtCore.QSize(QtCore.QRect(0,0,432,468).size()).expandedTo(QtLanguageSelectorGUI.minimumSizeHint()))

        self.gridlayout = QtGui.QGridLayout(QtLanguageSelectorGUI)
        self.gridlayout.setMargin(9)
        self.gridlayout.setSpacing(6)
        self.gridlayout.setObjectName("gridlayout")

        self.systemLanguageFrame = QtGui.QFrame(QtLanguageSelectorGUI)
        self.systemLanguageFrame.setFrameShape(QtGui.QFrame.NoFrame)
        self.systemLanguageFrame.setFrameShadow(QtGui.QFrame.Raised)
        self.systemLanguageFrame.setObjectName("systemLanguageFrame")

        self.gridlayout1 = QtGui.QGridLayout(self.systemLanguageFrame)
        self.gridlayout1.setMargin(9)
        self.gridlayout1.setSpacing(6)
        self.gridlayout1.setObjectName("gridlayout1")

        self.pushButtonCancel_2 = QtGui.QPushButton(self.systemLanguageFrame)
        self.pushButtonCancel_2.setObjectName("pushButtonCancel_2")
        self.gridlayout1.addWidget(self.pushButtonCancel_2,3,2,1,1)

        self.listBoxDefaultLanguage = QtGui.QListWidget(self.systemLanguageFrame)
        self.listBoxDefaultLanguage.setObjectName("listBoxDefaultLanguage")
        self.gridlayout1.addWidget(self.listBoxDefaultLanguage,1,0,1,3)

        self.pushButtonSetSystemLanguage = QtGui.QPushButton(self.systemLanguageFrame)
        self.pushButtonSetSystemLanguage.setObjectName("pushButtonSetSystemLanguage")
        self.gridlayout1.addWidget(self.pushButtonSetSystemLanguage,3,1,1,1)

        self.defaultSystemLabel = QtGui.QLabel(self.systemLanguageFrame)
        self.defaultSystemLabel.setWordWrap(False)
        self.defaultSystemLabel.setObjectName("defaultSystemLabel")
        self.gridlayout1.addWidget(self.defaultSystemLabel,0,0,1,2)

        spacerItem = QtGui.QSpacerItem(40,20,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Minimum)
        self.gridlayout1.addItem(spacerItem,3,0,1,1)

        self.enableInputMethods = QtGui.QCheckBox(self.systemLanguageFrame)
        self.enableInputMethods.setObjectName("enableInputMethods")
        self.gridlayout1.addWidget(self.enableInputMethods,2,0,1,3)
        self.gridlayout.addWidget(self.systemLanguageFrame,0,0,1,1)

        self.installLanguageFrame = QtGui.QFrame(QtLanguageSelectorGUI)
        self.installLanguageFrame.setFrameShape(QtGui.QFrame.NoFrame)
        self.installLanguageFrame.setFrameShadow(QtGui.QFrame.Raised)
        self.installLanguageFrame.setObjectName("installLanguageFrame")

        self.gridlayout2 = QtGui.QGridLayout(self.installLanguageFrame)
        self.gridlayout2.setMargin(9)
        self.gridlayout2.setSpacing(6)
        self.gridlayout2.setObjectName("gridlayout2")

        self.listViewLanguages = QtGui.QListWidget(self.installLanguageFrame)
        self.listViewLanguages.setObjectName("listViewLanguages")
        self.gridlayout2.addWidget(self.listViewLanguages,1,0,1,3)

        self.pushButtonOk = QtGui.QPushButton(self.installLanguageFrame)
        self.pushButtonOk.setObjectName("pushButtonOk")
        self.gridlayout2.addWidget(self.pushButtonOk,2,1,1,1)

        self.pushButtonCancel = QtGui.QPushButton(self.installLanguageFrame)
        self.pushButtonCancel.setObjectName("pushButtonCancel")
        self.gridlayout2.addWidget(self.pushButtonCancel,2,2,1,1)

        spacerItem1 = QtGui.QSpacerItem(40,20,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Minimum)
        self.gridlayout2.addItem(spacerItem1,2,0,1,1)

        self.selectLanguageLabel = QtGui.QLabel(self.installLanguageFrame)
        self.selectLanguageLabel.setWordWrap(False)
        self.selectLanguageLabel.setObjectName("selectLanguageLabel")
        self.gridlayout2.addWidget(self.selectLanguageLabel,0,0,1,2)
        self.gridlayout.addWidget(self.installLanguageFrame,1,0,1,1)

        self.retranslateUi(QtLanguageSelectorGUI)
        QtCore.QMetaObject.connectSlotsByName(QtLanguageSelectorGUI)

    def retranslateUi(self, QtLanguageSelectorGUI):
        QtLanguageSelectorGUI.setWindowTitle(QtGui.QApplication.translate("QtLanguageSelectorGUI", "Language Installer", None, QtGui.QApplication.UnicodeUTF8))
        self.pushButtonCancel_2.setText(QtGui.QApplication.translate("QtLanguageSelectorGUI", "Cancel", None, QtGui.QApplication.UnicodeUTF8))
        self.pushButtonSetSystemLanguage.setText(QtGui.QApplication.translate("QtLanguageSelectorGUI", "Set System Language", None, QtGui.QApplication.UnicodeUTF8))
        self.defaultSystemLabel.setText(QtGui.QApplication.translate("QtLanguageSelectorGUI", "Default system language:", None, QtGui.QApplication.UnicodeUTF8))
        self.enableInputMethods.setText(QtGui.QApplication.translate("QtLanguageSelectorGUI", "Enable support to enter complex characters", None, QtGui.QApplication.UnicodeUTF8))
        self.pushButtonOk.setText(QtGui.QApplication.translate("QtLanguageSelectorGUI", "Install", None, QtGui.QApplication.UnicodeUTF8))
        self.pushButtonCancel.setText(QtGui.QApplication.translate("QtLanguageSelectorGUI", "Cancel", None, QtGui.QApplication.UnicodeUTF8))
        self.selectLanguageLabel.setText(QtGui.QApplication.translate("QtLanguageSelectorGUI", "Select language to install:", None, QtGui.QApplication.UnicodeUTF8))
