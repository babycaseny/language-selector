
import sys
from qt import *

from LanguageSelector.LanguageSelector import *
from QtLanguageSelectorGUI import QtLanguageSelectorGUI
from gettext import gettext as _

class QtLanguageSelector(QtLanguageSelectorGUI,LanguageSelectorBase):
    """ actual implementation of the qt GUI """

    def __init__(self, app, datadir):
        LanguageSelectorBase.__init__(self, datadir)
        QtLanguageSelectorGUI.__init__(self)

        #self.listViewLanguages.addColumn( _("Translation"))
        self.init()
        self.parentApp = app
        # connect the signals
        app.connect(self.pushButtonOk,
                    SIGNAL("clicked()"),
                    self.onPushButtonOk)

    def init(self):
        self.openCache(apt.progress.OpProgress())
        self.updateLanguagesList()
        self.updateSystemDefaultCombobox()

    def updateSystemDefaultCombobox(self):
        print "updateSystemDefaultCombox()"
        self.comboBoxDefaultLanguage.clear()
        self._localeinfo.localeToCodeMap = {}
        # get the current default lang
        defaultLangName = None
        defaultLangCode = self.getSystemDefaultLanguage()
        if defaultLangCode:
            defaultLangName = self._localeinfo.translate(defaultLangCode)
        for locale in self._localeinfo.generated_locales():
            localeName = self._localeinfo.translate(locale)
            self.comboBoxDefaultLanguage.insertItem(localeName)
            self._localeinfo.localeToCodeMap[localeName] = locale
            if defaultLangName == self._localeinfo.translate(locale):
                print "found default: %s" % defaultLangName
                self.comboBoxDefaultLanguage.setCurrentText(defaultLangName)

    def updateLanguagesList(self):
        print "updateLanguageList()"
        self.listViewLanguages.clear()
        languageList = self._cache.getLanguageInformation()
        self._localeinfo.listviewStrToLangInfoMap = {}
        for lang in languageList:
            elm = QCheckListItem(self.listViewLanguages,
                                 lang.language,
                                 QCheckListItem.CheckBox)
            self._localeinfo.listviewStrToLangInfoMap[lang.language] = lang
            if lang.langPackInstalled and lang.langSupportInstalled:
                elm.setOn(True)
            elif lang.langPackInstalled or lang.langSupportInstalled:
                print "tristate: %s" % lang.language
                elm.setTristate(True)
                elm.activate()
            else:
                elm.setOn(False)
        #print elm.isOn()

    def run_pkg_manager(self, lock, to_inst, to_rm):
        if len(to_inst) > 0:
            subprocess.call(["adept_batch","install"]+to_inst)
        # then remove
        if len(to_rm) > 0:
            subprocess.call(["adept_batch","remove"]+to_rm)
        lock.release()

    def onPushButtonOk(self):
        #print "onPushButtonOk(self)"

        # update the default language box
        lang = self.comboBoxDefaultLanguage.currentText()
        new_locale = ("%s"%lang)
        try:
            new_code = self._localeinfo.localeToCodeMap[new_locale]
            self.setSystemDefaultLanguage(new_code)
        except KeyError:
            print "ERROR: can set new_locale: '%s'"%new_locale
            pass

        # see what needs to be installed
        elm = self.listViewLanguages.firstChild()
        while elm:
            li = self._localeinfo.listviewStrToLangInfoMap["%s"%elm.text()]
            inconsistent = li.langPackInstalled ^ li.langSupportInstalled
            was_installed = (li.langPackInstalled or li.langSupportInstalled)
            # it was installed and is now unselected
            if (inconsistent and elm.state() == QCheckListItem.Off):
                self._cache.tryRemoveLanguage(li.languageCode)
            elif (elm.state() == QCheckListItem.Off) and was_installed:
                self._cache.tryRemoveLanguage(li.languageCode)
            # it was not installed and is selected now
            elif (inconsistent and elm.state() == QCheckListItem.On):
                self._cache.tryInstallLanguage(li.languageCode)
            elif (elm.state() == QCheckListItem.On) and not was_installed:
                self._cache.tryInstallLanguage(li.languageCode)

            # ignore inconistent states for now
            elm = elm.itemBelow()
        (to_inst, to_rm) = self._cache.getChangesList()
        if len(to_inst) == len(to_rm) == 0:
            return
        print to_inst
        print to_rm

        # first install
        self.setEnabled(False)
        lock = thread.allocate_lock()
        lock.acquire()
        t = thread.start_new_thread(self.run_pkg_manager,(lock,to_inst,to_rm))
        while lock.locked():
            self.parentApp.processEvents()
            time.sleep(0.05)
        self.setEnabled(True)

        kdmscript = "/etc/init.d/kdm"
        if os.path.exists("/var/run/kdm.pid") and os.path.exists(kdmscript):
            subprocess.call(["invoke-rc.d","kdm","reload"])

        #self.run_pkg_manager(to_inst, to_rm)
        # re-init
        self.init()

if __name__ == "__main__":

    app = QApplication(sys.argv)
    
    lc = QtLanguageSelector(app, "/usr/share/language-selector/")
    app.setMainWidget(lc)
    
    lc.show()


    app.exec_loop()
    
