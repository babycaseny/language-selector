# (c) 2005 Canonical Ltd
# Author: Michael Vogt <michael.vogt@ubuntu.com>
# Author: Jonathan Riddell <jriddell@ubuntu.com>
#
# Released under the GNU GPL version 2 or later
#

import sys
from PyQt4.QtCore import *
from PyQt4.QtGui import *

from LanguageSelector.LanguageSelector import *
from QtLanguageSelectorGUI import Ui_QtLanguageSelectorGUI
from gettext import gettext as i18n

def utf8(str):
  if isinstance(str, unicode):
      return str
  return unicode(str, 'UTF-8')

def _(string):
    return unicode(i18n(string), "utf-8")

class QtLanguageSelector(QWidget,LanguageSelectorBase):
    """ actual implementation of the qt GUI """

    def __init__(self, app, datadir, mode):
        LanguageSelectorBase.__init__(self, datadir)
        QWidget.__init__(self)
        Ui_QtLanguageSelectorGUI.__init__(self)
        self.ui = Ui_QtLanguageSelectorGUI()
        self.ui.setupUi(self)

        self.parentApp = app

        self.setWindowIcon(QIcon("/usr/share/icons/crystalsvg/32x32/apps/locale.png"))
        self.ui.pushButtonSetSystemLanguage.setIcon(QIcon("/usr/share/icons/crystalsvg/22x22/actions/button_ok.png"))
        self.ui.pushButtonOk.setIcon(QIcon("/usr/share/icons/crystalsvg/22x22/actions/button_ok.png"))
        self.ui.pushButtonCancel.setIcon(QIcon("/usr/share/icons/crystalsvg/22x22/actions/button_cancel.png"))
        self.ui.pushButtonCancel_2.setIcon(QIcon("/usr/share/icons/crystalsvg/22x22/actions/button_cancel.png"))

        self.mode = mode
        self.init()
        if mode == "uninstall":
            self.ui.pushButtonOk.setText(_("Uninstall"))
            self.ui.selectLanguageLabel.setText(_("Select language to uninstall:"))
            self.ui.systemLanguageFrame.hide()
        elif mode == "install":
            self.ui.systemLanguageFrame.hide()
        elif mode == "select":
            self.ui.installLanguageFrame.hide()
            self.resize(self.sizeHint())
            self.setWindowTitle(_("Language Selector"))
        else:
            print "ERROR: unknown mode"

        # connect the signals
        app.connect(self.ui.listBoxDefaultLanguage, SIGNAL("itemSelectionChanged()"), self.check_input_methods)
        app.connect(self.ui.pushButtonOk, SIGNAL("clicked()"), self.onPushButtonOk)
        app.connect(self.ui.pushButtonSetSystemLanguage, SIGNAL("clicked()"), self.onSystemPushButtonOk)
        app.connect(self.ui.pushButtonCancel, SIGNAL("clicked()"), self.close)
        app.connect(self.ui.pushButtonCancel_2, SIGNAL("clicked()"), self.close)

    def init(self):
        self.translateUI()
        try:
            self.openCache(apt.progress.OpProgress())
        except ExceptionPkgCacheBroken:
            s = _("Software database is broken")
            # FIXME: mention adept here instead of synaptic, but the
            #        change happend during string freeze
            t = _("It is impossible to install or remove any software. "
                  "Please use the package manager \"Synaptic\" or run "
                  "\"sudo apt-get install -f\" in a terminal to fix "
                  "this issue at first.")
            QMessageBox.warning(self, s, t)
        self.updateLanguagesList()
        self.updateSystemDefaultListbox()

    def translateUI(self):
        """ translate the strings in the UI, needed because Qt designer doesn't use gettext """
        self.ui.defaultSystemLabel.setText(_("Default system language:"))
        self.ui.pushButtonSetSystemLanguage.setText(_("Set System Language"))
        self.ui.enableInputMethods.setText(_("Enable support to enter complex characters"))
        self.ui.pushButtonCancel_2.setText(_("Cancel"))
        self.ui.selectLanguageLabel.setText(_("Select language to install:"))
        self.ui.pushButtonOk.setText(_("Install"))
        self.ui.pushButtonCancel.setText(_("Cancel"))

    def updateSystemDefaultListbox(self):
        self.ui.listBoxDefaultLanguage.clear()
        self._localeinfo.localeToCodeMap = {}
        # get the current default lang
        defaultLangName = None
        defaultLangCode = self.getSystemDefaultLanguage()
        if defaultLangCode:
            defaultLangName = self._localeinfo.translate(defaultLangCode)
        locales = []
        for locale in self._localeinfo.generated_locales():
            name = utf8(self._localeinfo.translate(locale))
            locales.append(name)
            self._localeinfo.localeToCodeMap[name] = locale
        locales.sort()
        for localeName in locales:
            item = QListWidgetItem(localeName, self.ui.listBoxDefaultLanguage)
            if defaultLangName == localeName:
                item.setSelected(True)
        if (not os.path.exists("/etc/alternatives/xinput-all_ALL") or
            not os.path.exists("/usr/bin/im-switch")):
            self.ui.enableInputMethods.setEnabled(False)

    def updateLanguagesList(self):
        self.ui.listViewLanguages.clear()
        # get the language names and sort them alphabetically
        languageList = self._cache.getLanguageInformation()
        self._localeinfo.listviewStrToLangInfoMap = {}
        for lang in languageList:
            self._localeinfo.listviewStrToLangInfoMap[lang.language] = lang
        languages = self._localeinfo.listviewStrToLangInfoMap.keys()
        languages.sort()

        for langName in languages:
            lang = self._localeinfo.listviewStrToLangInfoMap[langName]
            elm = QListWidgetItem(utf8(lang.language), self.ui.listViewLanguages)
            if lang.langPackInstalled and lang.langSupportInstalled:
                if self.mode == "install":
                    elm.setFlags(Qt.ItemIsDropEnabled)  #not sure how to unset all flags, but this disables the item
                    elm.setToolTip(_("Already installed"))
                else:
                    elm.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            elif lang.langPackInstalled or lang.langSupportInstalled:
                elm.setToolTip(_("Partially Installed"))
            else:
                if self.mode == "uninstall":
                    elm.setFlags(Qt.ItemIsDropEnabled)  #not sure how to unset all flags, but this disables the item
                    elm.setToolTip(_("Not installed"))
                else:
                    elm.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

    def check_input_methods(self):
        """ check if the selected langauge has input method support
            and set checkbutton_enable_input_methods accordingly
        """
        if (os.path.exists("/etc/alternatives/xinput-all_ALL") and
            os.path.exists("/usr/bin/im-switch")):
            items = self.ui.listBoxDefaultLanguage.selectedItems()
            if len(items) == 1 and self.mode == "select":
                item = items[0]
                lang = item.text()
                new_locale = ("%s"%lang)
                try:
                    code = self._localeinfo.localeToCodeMap[new_locale]
                    # if we have a default in im-switch for this language, we
                    # can't change it from here (unless the im-switch swamp in drained)
                    default = os.path.exists("/etc/alternatives/xinput-%s" % code)
                    self.ui.enableInputMethods.setEnabled(not default) 
                    self.ui.enableInputMethods.setChecked(default)        # bah, Qt4 won't show it ticked when disabled
                    if default:
                        return
                    # now check if we have overwritten this - we do this by checking
                    # the setting for all_ALL (im-switch goodness again :/)
                    target = os.path.basename(os.readlink("/etc/alternatives/xinput-all_ALL"))
                    active = (target != "default" and target != "none")
                    self.ui.enableInputMethods.setChecked(active)
                except KeyError:
                    print "ERROR: can not find new_locale: '%s'"%new_locale

    def run_pkg_manager(self, lock, to_inst, to_rm):
        self.returncode = 0
        if len(to_inst) > 0:
            self.returncode = subprocess.call(["adept_batch","install"]+to_inst)
        # then remove
        if len(to_rm) > 0:
            self.returncode = subprocess.call(["adept_batch","remove"]+to_rm)
        lock.release()

    def onSystemPushButtonOk(self):
        (lang, code) = self.getSystemLanguage()
        self.setSystemDefaultLanguage(code)
        scimOn = self.updateInputMethods()
        if scimOn:
            QMessageBox.information(self, _("Language Set"), _("Default system Language now set to %s.  Complex character input will be enabled when you next log in.") % lang)
        else:
            QMessageBox.information(self, _("Language Set"), _("Default system Language now set to %s.") % lang)
        self.close()

    def __input_method_config_changed(self):
        """ check if we changed the input method config here         
        """
        if (os.path.exists("/etc/alternatives/xinput-all_ALL") and
            os.path.exists("/usr/bin/im-switch")):
          (lang, code) = self.getSystemLanguage()
          default = os.path.exists("/etc/alternatives/xinput-%s" % code)
          if default:
              return
          # now check if we have overwritten this - we do this by checking
          # the setting for all_ALL (im-switch goodness again :/)
          target = os.path.basename(os.readlink("/etc/alternatives/xinput-all_ALL"))
          current = (target != "default" and target != "none")
          new = (self.ui.enableInputMethods.checkState() == Qt.Checked)
          return (new != current)

    def updateInputMethods(self):
        """ write new input method defaults - currently we only support
            "im-switch -a" to reset and
            "im-switch -s scim" to set to scim (that is the default im
                              for all CJK languages currently)
        """
        (lang, code) = self.getSystemLanguage()
        # if something has changed - act!
        if self.__input_method_config_changed():
            if self.ui.enableInputMethods.checkState() == Qt.Checked:
                os.system("im-switch -z %s -s scim" % code)
                return True
            else:
                os.system("im-switch -z %s -a" % code)
                return False

    def getSystemLanguage(self):
        """ returns tuple of (lang, code) strings """
        items = self.ui.listBoxDefaultLanguage.selectedItems()
        if len(items) == 1 and self.mode == "select":
            item = items[0]
            lang = item.text()
            new_locale = ("%s"%lang)
            try:
                code = self._localeinfo.localeToCodeMap[new_locale]
                return (lang, code)
            except KeyError:
                print "ERROR: can not find new_locale: '%s'"%new_locale

    def onPushButtonOk(self):
        items = self.ui.listViewLanguages.selectedItems()
        if len(items) == 1:
            elm = items[0]
            li = self._localeinfo.listviewStrToLangInfoMap["%s"%elm.text().toUtf8()]
            if self.mode == "uninstall":
                self._cache.tryRemoveLanguage(li.languageCode)
            else:
                self._cache.tryInstallLanguage(li.languageCode)

        (to_inst, to_rm) = self._cache.getChangesList()
        if len(to_inst) == len(to_rm) == 0:
            self.close()
            return

        # first install
        self.setCursor(Qt.WaitCursor)
        self.setEnabled(False)
        lock = thread.allocate_lock()
        lock.acquire()
        t = thread.start_new_thread(self.run_pkg_manager,(lock,to_inst,to_rm))
        while lock.locked():
            self.parentApp.processEvents()
            time.sleep(0.05)
        self.setCursor(Qt.ArrowCursor)
        self.setEnabled(True)

        kdmscript = "/etc/init.d/kdm"
        if os.path.exists("/var/run/kdm.pid") and os.path.exists(kdmscript):
            subprocess.call(["invoke-rc.d","kdm","reload"])

        #self.run_pkg_manager(to_inst, to_rm)
        if self.returncode == 0 and self.mode == "install":
            QMessageBox.information( self, _("Language Installed"), _("Translations and support have now been installed for %s.  Select them from the Add Language button." % str(items[0].text())) )
        elif self.returncode == 0 and self.mode == "uninstall":
            QMessageBox.information( self, _("Language Uninstalled"), _("Translations and support have now been uninstalled for %s." % str(items[0].text())) )
        else:
            QMessageBox.warning(self, _("Language Not Set"), _("Failed to set system language."))
        self.close()

if __name__ == "__main__":

    app = QApplication(sys.argv)
    
    lc = QtLanguageSelector(app, "/usr/share/language-selector/", sys.argv[2])
    app.setMainWidget(lc)
    
    lc.show()


    app.exec_loop()
    
