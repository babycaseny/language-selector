# -*- coding: utf-8 -*-
#
# © 2005 Canonical Ltd
# © 2009 Harald Sitter
# Author: Michael Vogt <michael.vogt@ubuntu.com>
# Author: Jonathan Riddell <jriddell@ubuntu.com>
# Author: Harald Sitter <apachelogger@ubuntu.com>
#
# Released under the GNU GPL version 2 or later
#

import sys
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyKDE4.kdecore import ki18n, KAboutData, KCmdLineArgs, KCmdLineOptions
from PyKDE4.kdeui import KApplication, KIcon,  KMessageBox, KGuiItem

from LanguageSelector.LanguageSelector import *
from LanguageSelector.ImSwitch import ImSwitch
from QtLanguageSelectorGUI import Ui_QtLanguageSelectorGUI
from gettext import gettext as i18n

def utf8(str):
  if isinstance(str, unicode):
      return str
  return unicode(str, 'UTF-8')

def _(string):
    return utf8(i18n(string))

class QtLanguageSelector(QWidget,LanguageSelectorBase):
    """ actual implementation of the qt GUI """

    def __init__(self, app, datadir, mode):
        LanguageSelectorBase.__init__(self, datadir)
        QWidget.__init__(self)
        Ui_QtLanguageSelectorGUI.__init__(self)
        self.ui = Ui_QtLanguageSelectorGUI()
        self.ui.setupUi(self)

        self.parentApp = app

        self.setWindowIcon(KIcon("preferences-desktop-locale"))
        self.ui.pushButtonSetSystemLanguage.setIcon(KIcon("dialog-ok"))
        self.ui.pushButtonOk.setIcon(KIcon("dialog-ok"))
        self.ui.pushButtonCancel.setIcon(KIcon("dialog-cancel"))
        self.ui.pushButtonCancel_2.setIcon(KIcon("dialog-cancel"))

        self.imSwitch = ImSwitch()

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
            self.checkInputMethods()
        else:
            print "ERROR: unknown mode"

        # connect the signals
        app.connect(self.ui.listBoxDefaultLanguage, SIGNAL("itemSelectionChanged()"), self.checkInputMethods)
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
            t = _("It is impossible to install or remove any software. "
                  "Please use the package manager \"Adept\" or run "
                  "\"sudo apt-get install -f\" in a terminal to fix "
                  "this issue at first.")
            KMessageBox.Error(self, t, s)
        self.updateLanguagesList()
        self.updateSystemDefaultListbox()

        if not self._cache.havePackageLists:
            yesText = _("_Update").replace("_", "&")
            noText = _("_Remind Me Later").replace("_", "&")
            yes = KGuiItem(yesText, "dialog-ok")
            no = KGuiItem(noText, "process-stop")
            text = "<big><b>%s</b></big>\n\n%s" % (
              _("No language information available"),
              _("The system does not have information about the "
                "available languages yet. Do you want to perform "
                "a network update to get them now? "))
            text = text.replace("\n", "<br />")
            res = KMessageBox.questionYesNo(self, text, "", yes, no)
            if res == KMessageBox.Yes:
                self.setEnabled(False)
                self.update()
                self.openCache(apt.progress.OpProgress())
                self.updateLanguagesList()
                self.setEnabled(True)


        # see if something is missing
        if True: #options.verify_installed:
            self.verifyInstalledLangPacks()


    def translateUI(self):
        """ translate the strings in the UI, needed because Qt designer doesn't use gettext """
        self.ui.defaultSystemLabel.setText(_("Default system language:"))
        self.ui.pushButtonSetSystemLanguage.setText(_("Set System Language"))
        self.ui.labelInputMethod.setText(_("Keyboard input method:"))
        self.ui.pushButtonCancel_2.setText(_("Cancel"))
        self.ui.selectLanguageLabel.setText(_("Select language to install:"))
        self.ui.pushButtonOk.setText(_("Install"))
        self.ui.pushButtonCancel.setText(_("Cancel"))

    def updateSystemDefaultListbox(self):
        self.ui.listBoxDefaultLanguage.clear()
        self._localeinfo.localeToCodeMap = {}
        # get the current default lang
        defaultLangName = None
        defaultLangCode = self._localeinfo.getSystemDefaultLanguage()[0]
        if defaultLangCode:
            defaultLangName = utf8(self._localeinfo.translate(defaultLangCode, native=True))
        locales = []
        for locale in self._localeinfo.generated_locales():
            name = utf8(self._localeinfo.translate(locale, native=True))
            locales.append(name)
            self._localeinfo.localeToCodeMap[name] = locale
        locales.sort()
        for localeName in locales:
            item = QListWidgetItem(localeName, self.ui.listBoxDefaultLanguage)
            if defaultLangName == localeName:
                item.setSelected(True)
        if (not os.path.exists("/etc/alternatives/xinput-all_ALL") or
            not os.path.exists("/usr/bin/im-switch")):
            self.ui.comboBoxInputMethod.setEnabled(False)

    def verifyInstalledLangPacks(self):
        """ called at the start to inform about possible missing
            langpacks (e.g. gnome/kde langpack transition)
        """
        print "verifyInstalledLangPacks"
        missing = self.getMissingLangPacks()

        print "Missing: %s " % missing
        if len(missing) > 0:
            # FIXME: add "details"
            yesText = _("_Install").replace("_", "&")
            noText = _("_Remind Me Later").replace("_", "&")
            yes = KGuiItem(yesText, "dialog-ok")
            no = KGuiItem(noText, "process-stop")
            text = "<big><b>%s</b></big>\n\n%s" % (
                _("The language support is not installed completely"),
                _("Some translations or writing aids available for your "
                  "chosen languages are not installed yet. Do you want "
                  "to install them now?"))
            text = text.replace("\n", "<br />")
            res = KMessageBox.questionYesNo(self, text, "", yes, no)
            if res == KMessageBox.Yes:
                self.setEnabled(False)
                self.commit(missing, [])
                self.updateLanguagesList()
                self.setEnabled(True)

    def update(self):
        lock = thread.allocate_lock()
        lock.acquire()
        t = thread.start_new_thread(self.run_pkg_manager_update,(lock,))
        while lock.locked():
            self.parentApp.processEvents()
            time.sleep(0.05)

    def commit(self, inst, rm):
        # unlock here to make sure that lock/unlock are always run
        # pair-wise (and don't explode on errors)
        if len(inst) == 0 and len(rm) == 0:
            return
        lock = thread.allocate_lock()
        lock.acquire()
        t = thread.start_new_thread(self.run_pkg_manager,(lock,inst,rm))
        while lock.locked():
            self.parentApp.processEvents()
            time.sleep(0.05)

    def updateLanguagesList(self):
        self.ui.listViewLanguages.clear()
        # get the language names and sort them alphabetically
        languageList = self._cache.getLanguageInformation()
        self._localeinfo.listviewStrToLangInfoMap = {}
        for lang in languageList:
            self._localeinfo.listviewStrToLangInfoMap[utf8(lang.language)] = lang
        languages = self._localeinfo.listviewStrToLangInfoMap.keys()
        languages.sort()

        for langName in languages:
            lang = self._localeinfo.listviewStrToLangInfoMap[langName]
            elm = QListWidgetItem(utf8(lang.language), self.ui.listViewLanguages)

            if lang.fullInstalled:
                if self.mode == "install":
                    elm.setFlags(Qt.ItemIsDropEnabled)  #not sure how to unset all flags, but this disables the item
                    elm.setToolTip(_("Already installed"))
                else:
                    elm.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            elif lang.inconsistent:
                elm.setToolTip(_("Partially Installed"))
            else:
                if self.mode == "uninstall":
                    elm.setFlags(Qt.ItemIsDropEnabled)  #not sure how to unset all flags, but this disables the item
                    elm.setToolTip(_("Not installed"))
                    elm.setHidden(True)
                else:
                    elm.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

    def checkInputMethods(self):
        """ check if the selected langauge has input method support
            and set checkbutton_enable_input_methods accordingly
        """
        if not self.imSwitch.available():
            return
        (lang, code) = self.getSystemLanguage()

        combo = self.ui.comboBoxInputMethod
        combo.clear()

        currentIM = self.imSwitch.getInputMethodForLocale(code)
        if currentIM == None:
            currentIM = 'none'

        for (i, IM) in enumerate(self.imSwitch.getAvailableInputMethods()):
            combo.insertItem(i,IM)
            if IM == currentIM:
                combo.setCurrentIndex(i)

    def run_pkg_manager_update(self, lock):
        self.returncode = 0
        self.returncode = subprocess.call(["install-package","--update"])
        lock.release()

    def run_pkg_manager(self, lock, to_inst, to_rm):
        self.returncode = 0
        if len(to_inst) > 0:
            print str(["install-package","--install"]+to_inst)
            self.returncode = subprocess.call(["install-package","--install"]+to_inst)
        # then remove
        if len(to_rm) > 0:
            self.returncode = subprocess.call(["install-package","--uninstall"]+to_rm)
        lock.release()

    def onSystemPushButtonOk(self):
        (lang, code) = self.getSystemLanguage()
        self.writeLanguageSettings(sysLanguage=code, sysLang=code)
        self.updateInputMethods(code)
        KMessageBox.information(self, _("Default system Language now set to %s.") % lang, _("Language Set"))
        self.close()

    def updateInputMethods(self,code):
        IM_choice = self.ui.comboBoxInputMethod.currentText()
        self.imSwitch.setInputMethodForLocale(IM_choice, code)

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
            li = self._localeinfo.listviewStrToLangInfoMap[unicode(elm.text())]
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
            KMessageBox.information( self, _("Translations and support have now been installed for %s.  Select them from the Add Language button.") % unicode(items[0].text()), _("Language Installed") )
        elif self.returncode == 0 and self.mode == "uninstall":
            KMessageBox.information( self, _("Translations and support have now been uninstalled for %s.") % unicode(items[0].text()), _("Language Uninstalled") )
        else:
            KMessageBox.sorry(self, _("Failed to set system language."), _("Language Not Set"))
        self.close()

if __name__ == "__main__":

    appName     = "language-selector"
    catalog     = ""
    programName = ki18n ("Language Selector")
    version     = "0.3.4"
    description = ki18n ("Language Selector")
    license     = KAboutData.License_GPL
    copyright   = ki18n ("(c) 2008 Canonical Ltd")
    text        = ki18n ("none")
    homePage    = "https://launchpad.net/language-selector"
    bugEmail    = ""

    aboutData	= KAboutData (appName, catalog, programName, version, description, license, copyright, text, homePage, bugEmail)

    aboutData.addAuthor(ki18n("Rob Bean"), ki18n("PyQt4 to PyKDE4 port"))
    aboutData.addAuthor(ki18n("Harald Sitter"), ki18n("Developer"))

    options = KCmdLineOptions()
    options.add("!mode ", ki18n("REQUIRED: install, uninstall or select must follow"),  "select")
    options.add("+[install]", ki18n("install a language"))
    options.add("+[uninstall]", ki18n("uninstall a language"))
    options.add("+[select]", ki18n("select a language"))

    KCmdLineArgs.init (sys.argv, aboutData)
    KCmdLineArgs.addCmdLineOptions(options)

    gettext.bindtextdomain("language-selector", "/usr/share/locale")
    gettext.textdomain("language-selector")

    app = KApplication()

    args = KCmdLineArgs.parsedArgs()

    if args.isSet("mode"):
        whattodo = args.getOption("mode")
        if whattodo in ["install", "uninstall", "select"]:
            pass
        else:
            print whattodo, "is not a valid argument"
            args.usage()
    else:
        print "Please review the usage."
        args.usage()

    if os.getuid() != 0:
        KMessageBox.sorry(None, _("Please run this software with administrative rights."),  _("Not Root User"))
        sys.exit(1)

    lc = QtLanguageSelector(app, "/usr/share/language-selector/", whattodo)

    lc.show()

    app.exec_()

# kate: space-indent on; indent-width 4; mixedindent off; indent-mode python;
