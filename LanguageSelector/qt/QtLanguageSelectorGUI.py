import gettext
# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'QtLanguageSelectorGUI.ui'
#
# Created: Tue May 2 13:42:26 2006
#      by: The PyQt User Interface Compiler (pyuic) 3.15.1
#
# WARNING! All changes made in this file will be lost!


from qt import *


class QtLanguageSelectorGUI(QWidget):
    def __init__(self,parent = None,name = None,fl = 0):
        QWidget.__init__(self,parent,name,fl)

        if not name:
            self.setName("LanguageSelector")


        LanguageSelectorLayout = QGridLayout(self,1,1,11,6,"LanguageSelectorLayout")

        self.textLabel1 = QLabel(self,"textLabel1")

        LanguageSelectorLayout.addWidget(self.textLabel1,0,0)

        self.pushButtonCancel = QPushButton(self,"pushButtonCancel")

        LanguageSelectorLayout.addWidget(self.pushButtonCancel,4,2)

        self.pushButtonOk = QPushButton(self,"pushButtonOk")

        LanguageSelectorLayout.addWidget(self.pushButtonOk,4,1)

        self.listViewLanguages = QListView(self,"listViewLanguages")
        self.listViewLanguages.addColumn(gettext.gettext("Translation"))

        LanguageSelectorLayout.addMultiCellWidget(self.listViewLanguages,1,1,0,2)

        self.textLabel2 = QLabel(self,"textLabel2")

        LanguageSelectorLayout.addWidget(self.textLabel2,2,0)

        self.comboBoxDefaultLanguage = QComboBox(0,self,"comboBoxDefaultLanguage")

        LanguageSelectorLayout.addMultiCellWidget(self.comboBoxDefaultLanguage,3,3,0,2)

        self.languageChange()

        self.resize(QSize(581,421).expandedTo(self.minimumSizeHint()))
        self.clearWState(Qt.WState_Polished)

        self.connect(self.pushButtonCancel,SIGNAL("clicked()"),self.close)


    def languageChange(self):
        self.setCaption(gettext.gettext("Language selector"))
        self.textLabel1.setText(gettext.gettext("Supported Languages"))
        self.pushButtonCancel.setText(gettext.gettext("Close"))
        self.pushButtonOk.setText(gettext.gettext("Apply"))
        self.listViewLanguages.header().setLabel(0,gettext.gettext("Translation"))
        self.textLabel2.setText(gettext.gettext("Default language"))
        self.comboBoxDefaultLanguage.clear()
        self.comboBoxDefaultLanguage.insertItem(gettext.gettext("English"))


    def pushButtonOk_clicked(self):
        print "QtLanguageSelectorGUI.pushButtonOk_clicked(): Not implemented yet"

    def pushButtonCancel_released(self):
        print "QtLanguageSelectorGUI.pushButtonCancel_released(): Not implemented yet"
