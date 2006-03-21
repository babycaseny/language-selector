# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'QtLanguageSelectorGUI.ui'
#
# Created: Tue Mar 21 14:05:32 2006
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
        self.listViewLanguages.addColumn(self.__tr("Translation"))

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
        self.setCaption(self.__tr("Language selector"))
        self.textLabel1.setText(self.__tr("Supported Languages"))
        self.pushButtonCancel.setText(self.__tr("Cancel"))
        self.pushButtonOk.setText(self.__tr("Ok"))
        self.listViewLanguages.header().setLabel(0,self.__tr("Translation"))
        self.textLabel2.setText(self.__tr("Default language"))
        self.comboBoxDefaultLanguage.clear()
        self.comboBoxDefaultLanguage.insertItem(self.__tr("English"))


    def pushButtonOk_clicked(self):
        print "QtLanguageSelectorGUI.pushButtonOk_clicked(): Not implemented yet"

    def pushButtonCancel_released(self):
        print "QtLanguageSelectorGUI.pushButtonCancel_released(): Not implemented yet"

    def __tr(self,s,c = None):
        return qApp.translate("QtLanguageSelectorGUI",s,c)
