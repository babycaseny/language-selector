# (c) 2005 Canonical
# Author: Michael Vogt <michael.vogt@ubuntu.com>
#
# Released under the GPL
#

import pygtk
pygtk.require('2.0')
import gtk
import gtk.gdk
import gtk.glade
import pango
import gobject
import os.path
import string
import warnings
warnings.filterwarnings("ignore", "apt API not stable yet", FutureWarning)
import apt
import apt_pkg
import os.path
import shutil
import subprocess
import thread
import time
import gettext
import sys
import tempfile
import pwd

from gettext import gettext as _

 
(LIST_LANG,                     # language (i18n/human-readable)
 LIST_LANG_INFO                 # the short country code (e.g. de, pt_BR)
 ) = range(2)

(COMBO_LANGUAGE,
 COMBO_CODE) = range(2)



from LanguageSelector.gtk.SimpleGladeApp import SimpleGladeApp
from LanguageSelector.LocaleInfo import LocaleInfo
from LanguageSelector.LanguageSelector import *
from LanguageSelector.ImSwitch import ImSwitch

# intervals of the start up progress
# 3x caching and menu creation
STEPS_UPDATE_CACHE = [33, 66, 100]

class GtkProgress(apt.OpProgress):
    def __init__(self, host_window, progressbar, parent,
                 steps=STEPS_UPDATE_CACHE):
        # used for the "one run progressbar"
        self.steps = steps[:]
        self.base = 0
        self.old = 0
        self.next = int(self.steps.pop(0))

        self._parent = parent
        self._window = host_window
        self._progressbar = progressbar
        self._window.realize()
        host_window.window.set_functions(gtk.gdk.FUNC_MOVE)
        self._window.set_transient_for(parent)
    def update(self, percent):
        #print percent
        #print self.Op
        #print self.SubOp
        self._window.show()
        self._parent.set_sensitive(False)
        # if the old percent was higher, a new progress was started
        if self.old > percent:
            # set the borders to the next interval
            self.base = self.next
            try:
                self.next = int(self.steps.pop(0))
            except:
                pass
        progress = self.base + percent/100 * (self.next - self.base)
        self.old = percent
        self._progressbar.set_fraction(progress/100.0)
        while gtk.events_pending():
            gtk.main_iteration()
    def done(self):
        self._parent.set_sensitive(True)
    def hide(self):
        self._window.hide()

def xor(a,b): return a ^ b

class GtkLanguageSelector(LanguageSelectorBase,  SimpleGladeApp):

    def __init__(self, datadir, options):
        LanguageSelectorBase.__init__(self, datadir)
        SimpleGladeApp.__init__(self,
                                datadir+"/data/LanguageSelector.glade",
                                domain="language-selector")

        #build the combobox (with model)
        combo = self.combobox_default_lang
        model = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        cell = gtk.CellRendererText()
        combo.pack_start(cell, True)
        combo.add_attribute(cell, 'text', COMBO_LANGUAGE)
        combo.set_model(model)
        self.combo_dirty = False
        self.imSwitch = ImSwitch()

        # apply button
        self.button_apply.set_sensitive(False)

        # build the treeview
        self.setupTreeView()

        # show it
        self.window_main.show()
        self.setSensitive(False)
       
        self.updateLanguageView()
        self.updateSystemDefaultCombo()

        # see if something is missing
        if options.verify_installed:
            self.verifyInstalledLangPacks()

        if not self.imSwitch.available():
            self.checkbutton_enable_input_methods.set_sensitive(False)
        self.setSensitive(True)

    def setSensitive(self, value):
        if value:
            self.window_main.set_sensitive(True)
            self.window_main.window.set_cursor(None)
        else:
            self.window_main.set_sensitive(False)
            self.window_main.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
        while gtk.events_pending():
            gtk.main_iteration()

    def runAsRoot(self, userCmd):
        " run the given command as root using gksu "
        cmd = ["/usr/bin/gksu", 
               "--desktop", 
               "/usr/share/applications/language-selector.desktop", 
               "--"]
        ret = subprocess.call(cmd+userCmd)
        return (ret == 0)

    def setupTreeView(self):
        """ do all the treeview setup here """
        def toggle_cell_func(column, cell, model, iter):
            langInfo = model.get_value(iter, LIST_LANG_INFO)

            # check for active and inconsitent 
            inconsistent = langInfo.inconsistent
            #if inconsistent:
            #    print "%s is inconsistent" % langInfo.language

            # do we want to install or remove it?
            #toInstall = (langInfo.languagePkgList["languagePack"].doChange and \
            #            langInfo.languagePkgList["languageSupport"].doChange)
            #toRemove = (not langInfo.languagePkgList["languagePack"].doChange and \
            #            not langInfo.languagePkgList["languagePack"].doChange)
            # if it is going to be installed or removed, it can't
            # be inconsitent
            #if inconsistent and (toInstall or toRemove):
            #    inconsistent = False
                
            #cell.set_property("active", toInstall)
            cell.set_property("active", langInfo.fullInstalled)
            cell.set_property("inconsistent", inconsistent)
            
        def lang_view_func(cell_layout, renderer, model, iter):
            langInfo = model.get_value(iter, LIST_LANG_INFO)
            inconsistent = langInfo.inconsistent
            #current = langInfo.languagePkgList["languagePack"].installed or langInfo.languagePkgList["languageSupport"].installed
            #toInstall = langInfo.languagePkgList["languagePack"].doChange and langInfo.languagePkgList["languageSupport"].doChange
            #toRemove =  not langInfo.languagePkgList["languagePack"].doChange and not langInfo.languagePkgList["languageSupport"].doChange
            #if (not inconsistent and current != toInstall) or (inconsistent and (toInstall or toRemove)):
            if (langInfo.changes) :
                markup = "<b>%s</b>" % langInfo.language
            else:
                markup = "%s" % langInfo.language
            renderer.set_property("markup", markup)

        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(_("Language"), renderer, text=LIST_LANG)
        column.set_property("expand", True)
        column.set_cell_data_func (renderer, lang_view_func)
        self.treeview_languages.append_column(column)

        renderer= gtk.CellRendererToggle()
        renderer.connect("toggled", self.on_toggled)
        column = gtk.TreeViewColumn(_("Support"), renderer)
                                    #active=LIST_TRANSLATION,
                                    #inconsistent=LIST_TRANSLATION_PARTIAL)
        column.set_cell_data_func (renderer, toggle_cell_func)
        self.treeview_languages.append_column(column)
        # build the store
        self._langlist = gtk.ListStore(str, gobject.TYPE_PYOBJECT)
        self.treeview_languages.set_model(self._langlist)

    def _get_langinfo_on_cursor(self):
        (path, column) = self.treeview_languages.get_cursor ()
        if not path:
            return None
        iter = self._langlist.get_iter(path)
        langInfo = self._langlist.get_value(iter, LIST_LANG_INFO)
        return langInfo

    # details checkboxes
    def on_checkbutton_fonts_clicked(self, button):
        if self.block_toggle: return
        langInfo = self._get_langinfo_on_cursor()
        langInfo.languagePkgList["languageSupportFonts"].doChange = not langInfo.languagePkgList["languageSupportFonts"].doChange
        self.check_apply_button()
        self.treeview_languages.queue_draw()
        #self.debug_pkg_status()
    def on_checkbutton_input_methods_clicked(self, button):
        if self.block_toggle: return
        langInfo = self._get_langinfo_on_cursor()
        langInfo.languagePkgList["languageSupportInputMethods"].doChange = not langInfo.languagePkgList["languageSupportInputMethods"].doChange
        self.check_apply_button()
        self.treeview_languages.queue_draw()
        #self.debug_pkg_status()
    def on_checkbutton_writing_aids_clicked(self, button):
        if self.block_toggle: return
        langInfo = self._get_langinfo_on_cursor()
        langInfo.languagePkgList["languageSupportWritingAids"].doChange = not langInfo.languagePkgList["languageSupportWritingAids"].doChange
        self.check_apply_button()
        self.treeview_languages.queue_draw()
        #self.debug_pkg_status()
    def on_checkbutton_basic_translations_clicked(self, button):
        if self.block_toggle: return
        langInfo = self._get_langinfo_on_cursor()
        langInfo.languagePkgList["languagePack"].doChange = not langInfo.languagePkgList["languagePack"].doChange
        self.check_apply_button()
        self.treeview_languages.queue_draw()
        #self.debug_pkg_status()
    def on_checkbutton_extra_translations_clicked(self, button):
        if self.block_toggle: return
        langInfo = self._get_langinfo_on_cursor()
        langInfo.languagePkgList["languageSupportTranslations"].doChange = not langInfo.languagePkgList["languageSupportTranslations"].doChange
        self.check_apply_button()
        self.treeview_languages.queue_draw()
        #self.debug_pkg_status()
    def on_checkbutton_extra_clicked(self, button):
        if self.block_toggle: return
        langInfo = self._get_langinfo_on_cursor()
        langInfo.languagePkgList["languageSupportExtra"].doChange = not langInfo.languagePkgList["languageSupportExtra"].doChange
        self.check_apply_button()
        self.treeview_languages.queue_draw()
        #self.debug_pkg_status()

    # the global toggle
    def on_toggled(self, renderer, path_string):
        """ called when on install toggle """
        iter = self._langlist.get_iter_from_string(path_string)
        langInfo = self._langlist.get_value(iter, LIST_LANG_INFO)

        # special handling for inconsistent state
        #inconsistent = False  #xor(langInfo.languagePkgList["languagePack"].installed, langInfo.languagePkgList["languageSupport"].installed)
        # check if we already set remove 
        #toInstall = langInfo.languagePkgList["languagePack"].doChange and langInfo.languagePkgList["languageSupport"].doChange
        #toRemove = not langInfo.languagePkgList["languagePack"].doChange and not langInfo.languagePkgList["languageSupport"].doChange
        # if it is inconistent and wasn't touched yet, set it for install
        # from then on it will just work (tm)
        if langInfo.inconsistent :
            for pkg in langInfo.languagePkgList.values() :
                if (pkg.available and not pkg.installed) : 
                    pkg.doChange = True
        elif langInfo.fullInstalled :
            for pkg in langInfo.languagePkgList.values() :
                if (pkg.available) :
                    if (not pkg.installed and pkg.doChange) :
                        pkg.doChange = False
                    elif (pkg.installed and not pkg.doChange) :
                        pkg.doChange = True
        else :
            for pkg in langInfo.languagePkgList.values() :
                if (pkg.available) :
                    if (pkg.installed and pkg.doChange) :
                        pkg.doChange = False
                    elif (not pkg.installed and not pkg.doChange) :
                        pkg.doChange = True

        self.check_apply_button()
        self.treeview_languages.queue_draw()
        #self.debug_pkg_status()

    def on_treeview_languages_cursor_changed(self, treeview):
        #print "on_treeview_languages_cursor_changed()"
        langInfo = self._get_langinfo_on_cursor()
        for (button, attr) in ( 
              ("checkbutton_basic_translations", langInfo.languagePkgList["languagePack"]),
              ("checkbutton_extra_translations", langInfo.languagePkgList["languageSupportTranslations"]),
              ("checkbutton_writing_aids", langInfo.languagePkgList["languageSupportWritingAids"]),
              ("checkbutton_input_methods", langInfo.languagePkgList["languageSupportInputMethods"]),
              ("checkbutton_extra", langInfo.languagePkgList["languageSupportExtra"]),
              ("checkbutton_fonts", langInfo.languagePkgList["languageSupportFonts"])  ):
            self.block_toggle = True
            if ((attr.installed and not attr.doChange) or (not attr.installed and attr.doChange)) :
                getattr(self, button).set_active(True)
            else :
                getattr(self, button).set_active(False)
            getattr(self, button).set_sensitive(attr.available)
            self.block_toggle = False
            #self.debug_pkg_status()

    def debug_pkg_status(self):
        langInfo = self._get_langinfo_on_cursor()
        for pkg in langInfo.languagePkgList.items() :
            print ("%s, available: %s, installed: %s, doChange: %s" % (pkg[0], pkg[1].available, pkg[1].installed, pkg[1].doChange))
        print ("inconsistent? : %s" % langInfo.inconsistent)

    def check_apply_button(self):
        changed = False
        for (lang, langInfo) in self._langlist:
            if langInfo.changes:
                changed = True
        if self.combo_dirty or changed:
            self.button_apply.set_sensitive(True)
        else:
            self.button_apply.set_sensitive(False)

    def on_combobox_default_lang_changed(self, widget):
        self.combo_dirty = True
        self.check_input_methods()
        self.check_apply_button()

    def check_input_methods(self):
        """ check if the selected langauge has input method support
            and set checkbutton_enable_input_methods accordingly
        """
        if not self.imSwitch.available():
            return
        # get current selected default language
        combo = self.combobox_default_lang
        model = combo.get_model()
        if combo.get_active() < 0:
            return
        (lang, code) = model[combo.get_active()]
        # check if that has a im-switch config
        active = self.imSwitch.enabledForLocale(code)
        self._blockSignals = True
        self.checkbutton_enable_input_methods.set_active(active)
        self._blockSignals = False

    def writeInputMethodConfig(self):
        """ 
        write new input method defaults - currently we only support all_ALL
        """
        combo = self.combobox_default_lang
        model = combo.get_model()
        if combo.get_active() < 0:
            return
        (lang, code) = model[combo.get_active()]
        # check if we need to do something
        new_value = self.checkbutton_enable_input_methods.get_active()
        if self.imSwitch.enabledForLocale(code) != new_value:
            if new_value:
                self.imSwitch.enable(code)
            else:
                self.imSwitch.disable(code)
            #self.showRebootRequired()
            self.checkReloginNotification()

    def on_checkbutton_enable_input_methods_toggled(self, widget):
        if self._blockSignals:
            return
        #print "on_checkbutton_enable_input_methods_toggled()"
        active = self.checkbutton_enable_input_methods.get_active()
        self.combo_dirty = True
        self.check_apply_button()

    def build_commit_lists(self):
        # FIXME: add support to install only subsets of the 
        #        language - use langInfo.languagePkgList["languageSupport"]{Fonts,WritingAids,..}.{install,doChange} for this
        for (lang, langInfo) in self._langlist:
            #inconsistent = xor(langInfo.languagePkgList["languagePack"].installed, langInfo.languagePkgList["languageSupport"].installed)

            #wasInstalled = langInfo.languagePkgList["languagePack"].installed and langInfo.languagePkgList["languageSupport"].installed
            #wasNotInstalled = not langInfo.languagePkgList["languagePack"].installed and not langInfo.languagePkgList["languageSupport"].installed

            #toInstall = langInfo.languagePkgList["languagePack"].doChange and langInfo.languagePkgList["languageSupport"].doChange
            #toRemove = not langInfo.languagePkgList["languagePack"].doChange and not langInfo.languagePkgList["languageSupport"].doChange
            #if (inconsistent and toInstall) or (toInstall and wasNotInstalled):
            #    self._cache.tryInstallLanguage(langInfo.languageCode)
            #if (inconsistent and toRemove) or (toRemove and wasInstalled):
            #    self._cache.tryRemoveLanguage(langInfo.languageCode)
            self._cache.tryChangeDetails(langInfo)
        (to_inst, to_rm) = self._cache.getChangesList()
        #print "inst: %s" % to_inst
        #print "rm: %s" % to_rm
        return (to_inst, to_rm)

    def verify_commit_lists(self, inst_list, rm_list):
        """ verify if the selected package can actually be installed """
        res = True
        try:
            for pkg in inst_list:
                if self._cache.has_key(pkg):
                    self._cache[pkg].markInstall()
            for pkg in rm_list:
                if self._cache.has_key(pkg):
                    self._cache[pkg].markDelete()
        except SystemError:
            res = False

        # undo the selections
        self._cache.clear()
        if self._cache._depcache.BrokenCount != 0:
            # undoing the selections was impossible, 
            d = gtk.MessageDialog(parent=self.window_main,
                                  flags=gtk.DIALOG_MODAL,
                                  type=gtk.MESSAGE_ERROR,
                                  buttons=gtk.BUTTONS_CLOSE)
            d.set_markup("<big><b>%s</b></big>\n\n%s" % (
                _("Could not install the selected language support"),
                _("This is perhaps a bug of this application. Please "
                  "file a bug report at "
                  "https://launchpad.net/bugs/bugs/+package/ against "
                  "the 'language-selector' product.")))
            d.set_title=("")
            res = d.run()
            d.destroy()
            # something went pretty bad, re-get a cache
            progress = GtkProgress(self.dialog_progress,
                                   self.progressbar_cache,
                                   self.window_main)
            self._cache = apt.Cache(self._localeinfo, progress)
            progress.hide()
            res = False
        return res

    def commitAllChanges(self):
        """ 
        commit helper, builds the commit lists, verifies it
        
        returns the number of install/removed packages
        """
        self.setSensitive(False)
        # install the new packages (if any)
        (inst_list, rm_list) = self.build_commit_lists()
        if not self.verify_commit_lists(inst_list, rm_list):
            d = gtk.MessageDialog(parent=self.window_main,
                                  flags=gtk.DIALOG_MODAL,
                                  type=gtk.MESSAGE_ERROR,
                                  buttons=gtk.BUTTONS_CLOSE)
            d.set_markup("<big><b>%s</b></big>\n\n%s" % (
                _("Could not install the full language support"),
                _("Usually this is related to an error in your "
                  "software archive or software manager. Check your "
                  "software preferences in the menu \"Adminstration\".")))
            d.set_title("")
            d.run()
            d.destroy()
            self.setSensitive(True)
            return 0
        #print "inst_list: %s " % inst_list
        #print "rm_list: %s " % rm_list
        self.commit(inst_list, rm_list)

        # write input method config
        self.writeInputMethodConfig()

        # write the system default language
        if self.writeSystemDefaultLang():
            # queue a restart of gdm (if it is runing) to make the new
            # locales usable
            gdmscript = "/etc/init.d/gdm"
            if os.path.exists("/var/run/gdm.pid") and os.path.exists(gdmscript):
                self.runAsRoot(["invoke-rc.d","gdm","reload"])
        self.setSensitive(True)
        return len(inst_list)+len(rm_list)

    def on_button_ok_clicked(self, widget):
        self.commitAllChanges()
        gtk.main_quit()

    def on_button_apply_clicked(self, widget):
        if self.commitAllChanges() > 0:
            self.updateLanguageView()
        self.updateSystemDefaultCombo()

    def run_synaptic(self, lock, inst, rm, id):
        # FIXME: use self.runAsRoot() here
        cmd = ["gksu", 
               "--desktop", "/usr/share/applications/language-selector.desktop", 
               "--",
               "/usr/sbin/synaptic", "--hide-main-window",
               "--non-interactive", 
               "--parent-window-id", "%s" % (id),
               "--finish-str", _("The list of available languages on the "
                                 "system has been updated.")
               ]
        f = tempfile.NamedTemporaryFile()        
        cmd.append("--set-selections-file")
        cmd.append(f.name)
        for s in inst:
            f.write("%s\tinstall\n" % s)
        for s in rm:
            f.write("%s\tdeinstall\n" % s)
        f.flush()
        subprocess.call(cmd)
        lock.release()

    def commit(self, inst, rm):
        # unlock here to make sure that lock/unlock are always run
        # pair-wise (and don't explode on errors)
        if len(inst) == 0 and len(rm) == 0:
            return
        lock = thread.allocate_lock()
        lock.acquire()
        t = thread.start_new_thread(self.run_synaptic,(lock,inst,rm, self.window_main.window.xid))
        while lock.locked():
            while gtk.events_pending():
                gtk.main_iteration()
            time.sleep(0.05)

    def checkReloginNotification(self):
        #" display a reboot required notification "
        #rb = "/usr/share/update-notifier/notify-reboot-required"
        #if (hasattr(self, "install_result") and 
        #    self.install_result == 0 and
        #    os.path.exists(rb)):
        #    self.runAsRoot([rb])
        #    s = "/var/lib/update-notifier/dpkg-run-stamp"
        #    if os.path.exists(s):
        #        self.runAsRoot(["touch",s])
        #return True
        language_support_dir = '/usr/share/language-support'
        update_notifier_dir = '/var/lib/update-notifier/user.d'
        note = 'restart_session_required.note'
        notepath = os.path.join(language_support_dir, note)
        if os.path.exists(notepath):
            if not os.path.exists(update_notifier_dir):
                runAsRoot(["mkdir",update_notifier_dir])
            s = os.path.join(update_notifier_dir, note)
            if os.path.exists(s):
                self.runAsRoot(["touch",s])
            else :
                rb = "cp %s %s" % (notepath, s)
                self.runAsRoot([rb])
            s = "/var/lib/update-notifier/dpkg-run-stamp"
            if os.path.exists(s):
                self.runAsRoot(["touch",s])
        return True

    def on_button_cancel_clicked(self, widget):
        #print "button_cancel"
        gtk.main_quit()

    def on_delete_event(self, event, data):
        if self.window_main.get_property("sensitive") is False:
            return True
        else:
            gtk.main_quit()

    def verifyInstalledLangPacks(self):
        """ called at the start to inform about possible missing
            langpacks (e.g. gnome/kde langpack transition)
        """
        #print "verifyInstalledLangPacks"
        missing = []
        for (lang, langInfo) in self._langlist:
            trans_package = "language-pack-%s" % langInfo.languageCode
            # we have a langpack installed, see if we have all of it
            # (for hoary -> breezy transition)
            if self._cache.has_key(trans_package) and \
               self._cache[trans_package].isInstalled:
                #print "IsInstalled: %s " % trans_package
                for (pkg, translation) in self._cache.pkg_translations:
                    missing += self.missingTranslationPkgs(pkg, translation+langInfo.languageCode)

        #print "Missing: %s " % missing
        if len(missing) > 0:
            # FIXME: add "details"
            d = gtk.MessageDialog(parent=self.window_main,
                                  flags=gtk.DIALOG_MODAL,
                                  type=gtk.MESSAGE_QUESTION)
            d.set_markup("<big><b>%s</b></big>\n\n%s" % (
                _("The language support is not installed completely"),
                _("Some translations or writing aids available for your "
                  "chosen languages are not installed yet. Do you want "
                  "to install them now?")))
            d.add_buttons(_("_Remind Me Later"), gtk.RESPONSE_NO,
                          _("_Install"), gtk.RESPONSE_YES)
            d.set_default_response(gtk.RESPONSE_YES)
            d.set_title("")
            expander = gtk.Expander(_("Details"))
            scroll = gtk.ScrolledWindow()
            scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
            textview = gtk.TextView()
            textview.set_cursor_visible(False)
            textview.set_editable(False)
            buf = textview.get_buffer()
            pkgs = ""
            for pkg in missing:
                pkgs += "%s\n" % pkg
            buf.set_text(pkgs)
            buf.place_cursor(buf.get_start_iter())
            expander.add(scroll)
            scroll.add(textview)
            d.vbox.pack_start(expander)
            expander.show_all()
            res = d.run()
            d.destroy()
            if res == gtk.RESPONSE_YES:
                self.setSensitive(False)
                self.commit(missing, [])
                self.updateLanguageView()
                self.setSensitive(True)

    def updateLanguageView(self):
        #print "updateLanguageView()"
        self._langlist.clear()

        progress = GtkProgress(self.dialog_progress, self.progressbar_cache,
                               self.window_main)
        try:
            self.openCache(progress)
            progress.hide()
        except ExceptionPkgCacheBroken:
            d = gtk.MessageDialog(parent=self.window_main,
                                  flags=gtk.DIALOG_MODAL,
                                  type=gtk.MESSAGE_ERROR,
                                  buttons=gtk.BUTTONS_CLOSE)
            d.set_markup("<big><b>%s</b></big>\n\n%s" % (
                _("Software database is broken"),
                _("It is impossible to install or remove any software. "
                  "Please use the package manager \"Synaptic\" or run "
                  "\"sudo apt-get install -f\" in a terminal to fix "
                  "this issue at first.")))
            d.set_title("")
            d.run()
            d.destroy()
            sys.exit(1)

        languageList = self._cache.getLanguageInformation()
        #print "ll size: ", len(languageList)
        #print "ll type: ", type(languageList)
        for lang in languageList:
            #print "langInfo: %s" % lang
            inconsistent = lang.inconsistent
            #if inconsistent:
            #    print "inconsistent", lang.language
            installed = lang.fullInstalled
            self._langlist.append([_(lang.language), lang])
        self._langlist.set_sort_column_id(LIST_LANG, gtk.SORT_ASCENDING)
        for button in ( 
              "checkbutton_basic_translations",
              "checkbutton_extra_translations",
              "checkbutton_writing_aids",
              "checkbutton_input_methods",
              "checkbutton_extra",
              "checkbutton_fonts"):
            self.block_toggle = True
            getattr(self, button).set_active(False)
            getattr(self, button).set_sensitive(False)
            self.block_toggle = False

    def writeSystemDefaultLang(self):
        combo = self.combobox_default_lang
        model = combo.get_model()
        if combo.get_active() < 0:
            return
        (lang, code) = model[combo.get_active()]
        old_code = self._localeinfo.getDefaultLanguage()
        # no changes, nothing to do
        if old_code == code:
            return False
        self.setSystemDefaultLanguage(code)
        #self.showRebootRequired()
        self.checkReloginNotification()
        return True

    def showRebootRequired(self):
        " show a message box that a restart is required "
        d = gtk.MessageDialog(parent=self.window_main,
                              flags=gtk.DIALOG_MODAL,
                              type=gtk.MESSAGE_INFO,
                              buttons=gtk.BUTTONS_CLOSE)
        d.set_markup("<big><b>%s</b></big>\n\n%s" % (
                _("Reboot required"),
                _("To complete the changes a reboot is required so "
                  "that the new functionality is activated.")
                ))
        d.set_title=("")
        res = d.run()
        d.destroy()
        

    def updateSystemDefaultCombo(self):
        #print "updateSystemDefault()"
        combo = self.combobox_default_lang
        cell = combo.get_child().get_cell_renderers()[0]
        # FIXME: use something else than a hardcoded value here
        cell.set_property("wrap-width",300)
        cell.set_property("wrap-mode",pango.WRAP_WORD)
        model = combo.get_model()
        model.clear()

        # find the default
        defaultLangName = None
        defaultLangCode = self.getSystemDefaultLanguage()
        if defaultLangCode:
            defaultLangName = self._localeinfo.translate(defaultLangCode)

        # find out about the other options        
        i=0
        for locale in self._localeinfo.generated_locales():
            iter = model.append()
            model.set(iter,
                      COMBO_LANGUAGE,self._localeinfo.translate(locale),
                      COMBO_CODE, locale)
            if defaultLangName and \
                   self._localeinfo.translate(locale) == defaultLangName:
                combo.set_active(i)
            i+=1
            
        # reset the state of the apply button
        self.combo_dirty = False
        self.check_apply_button()
