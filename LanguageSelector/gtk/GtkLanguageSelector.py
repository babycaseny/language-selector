# (c) 2005 Canonical
# Author: Michael Vogt <michael.vogt@ubuntu.com>
#
# Released under the GPL
#

import gettext
import grp
import locale
import os
import pwd
import re
import shutil
import string
import subprocess
import sys
import thread
import time
import tempfile
from gettext import gettext as _

import gobject
from gi.repository import Gdk, Gtk, Pango
Gtk.require_version('2.0')

import apt
import apt_pkg

import aptdaemon.client
from defer import inline_callbacks
from aptdaemon.enums import *
from aptdaemon.gtk3widgets import AptProgressDialog

from LanguageSelector.LocaleInfo import LocaleInfo
from LanguageSelector.LanguageSelector import *
from LanguageSelector.ImSwitch import ImSwitch
from LanguageSelector.macros import *
 
(LIST_LANG,                     # language (i18n/human-readable)
 LIST_LANG_INFO                 # the short country code (e.g. de, pt_BR)
 ) = range(2)

(LANGTREEVIEW_LANGUAGE,
 LANGTREEVIEW_CODE) = range(2)
 
(IM_CHOICE,
 IM_NAME) = range(2)


def xor(a,b):
    " helper to simplify the reading "
    return a ^ b

def blockSignals(f):
    " decorator to ensure that the signals are blocked "
    def wrapper(*args, **kwargs):
        args[0]._blockSignals = True
        res = f(*args, **kwargs)
        args[0]._blockSignals = False
        return res
    return wrapper

def honorBlockedSignals(f):
    " decorator to ensure that the signals are blocked "
    def wrapper(*args, **kwargs):
        if args[0]._blockSignals:
            return
        res = f(*args, **kwargs)
        return res
    return wrapper

def insensitive(f):
    """
    decorator to ensure that a given function is run insensitive
    warning: this will not stack well so don't use it for nested
    stuff (a @insensitive func calling a @insensitve one)
    """
    def wrapper(*args, **kwargs):
        args[0].setSensitive(False)
        res = f(*args, **kwargs)
        args[0].setSensitive(True)
    return wrapper



# intervals of the start up progress
# 3x caching and menu creation
STEPS_UPDATE_CACHE = [33, 66, 100]

class GtkProgress(apt.progress.base.OpProgress):
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
        host_window.get_window().set_functions(Gdk.WMFunction.MOVE)
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
        while Gtk.events_pending():
            Gtk.main_iteration()
    def done(self):
        self._parent.set_sensitive(True)
    def hide(self):
        self._window.hide()

class GtkLanguageSelector(LanguageSelectorBase):

    def __init__(self, datadir, options):
        LanguageSelectorBase.__init__(self, datadir)
        self._datadir = datadir

        self.widgets = Gtk.Builder()
        self.widgets.set_translation_domain('language-selector')
        self.widgets.add_from_file(datadir+"/data/LanguageSelector.ui")
        self.widgets.connect_signals(self)

        self.is_admin = (os.getuid() == 0 or
                         grp.getgrnam("admin")[2] in os.getgroups())

        # see if we have any other human users on this system
        self.has_other_users = False
        num = 0
        for l in pwd.getpwall():
            if l.pw_uid >= 500 and l.pw_uid < 65534:
                num += 1
            if num >= 2:
                self.has_other_users = True
                break
        
        #build the comboboxes (with model)
        combo = self.combobox_locale_chooser
        model = Gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        cell = Gtk.CellRendererText()
        combo.pack_start(cell, True)
        combo.add_attribute(cell, 'text', LANGTREEVIEW_LANGUAGE)
        combo.set_model(model)
#        self.combo_syslang_dirty = False

#        combo = self.combobox_user_language
#        model = Gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
#        cell = Gtk.CellRendererText()
#        combo.pack_start(cell, True)
#        combo.add_attribute(cell, 'text', COMBO_LANGUAGE)
#        combo.set_model(model)
#        self.combo_userlang_dirty = False
        self.options = options

        # get aptdaemon client
        self.ac = aptdaemon.client.AptClient()

        combo = self.combobox_input_method
        model = Gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        cell = Gtk.CellRendererText()
        combo.pack_start(cell, True)
        combo.add_attribute(cell, 'text', IM_NAME)
        combo.set_model(model)
        self.imSwitch = ImSwitch()
        self._blockSignals = False

        # remove dangling ImSwitch symlinks if present
        self.imSwitch.removeDanglingSymlinks()

        # build the treeview
        self.setupLanguageTreeView()
        if self.is_admin:
            self.setupInstallerTreeView()
            self.updateLanguageView()
#        self.updateUserDefaultCombo()
        self.updateLocaleChooserCombo()
        self.check_input_methods()
#        self.updateSyncButton()
        
        # apply button
        self.button_apply.set_sensitive(False)

        # 'Apply System-Wide...' and 'Install/Remove Languages...' buttons
        if self.is_admin:
            self.button_apply_system_wide_languages.set_sensitive(True)
            self.button_install_remove_languages.set_sensitive(True)
            self.button_apply_system_wide_locale.set_sensitive(True)
        else:
            self.button_apply_system_wide_languages.set_sensitive(False)
            self.button_install_remove_languages.set_sensitive(False)
            self.button_apply_system_wide_locale.set_sensitive(False)

        # show it
        self.window_main.show()
        self.setSensitive(False)

        if self.is_admin:
            # check if the package list is up-to-date
            if not self._cache.havePackageLists:
                d = Gtk.MessageDialog(parent=self.window_main,
                                      flags=Gtk.DialogFlags.MODAL,
                                      type=Gtk.MessageType.INFO,
                                      buttons=Gtk.ButtonsType.CANCEL)
                d.set_markup("<big><b>%s</b></big>\n\n%s" % (
                    _("No language information available"),
                    _("The system does not have information about the "
                      "available languages yet. Do you want to perform "
                      "a network update to get them now? ")))
                d.set_title=("")
                d.add_button(_("_Update"), Gtk.ResponseType.YES)
                res = d.run()
                d.destroy()
                if res == Gtk.ResponseType.YES:
                    self.setSensitive(False)
                    self.update()
                    self.updateLanguageView()
                    self.setSensitive(True)

            # see if something is missing
            if self.options.verify_installed:
                self.verifyInstalledLangPacks()

        if not self.imSwitch.available():
            self.combobox_input_method.set_sensitive(False)
        self.setSensitive(True)

    def __getattr__(self, name):
        '''Convenient access to GtkBuilder objects'''

        o = self.widgets.get_object(name)
        if o is None:
            raise AttributeError, 'No such widget: ' + name
        return o

    def run(self):
        Gtk.main()

    def setSensitive(self, value):
        if value:
            self.window_main.set_sensitive(True)
            self.window_main.get_window().set_cursor(None)
        else:
            self.window_main.set_sensitive(False)
            self.window_main.get_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.WATCH))
        while Gtk.events_pending():
            Gtk.main_iteration()

#    @blockSignals
#    def updateSyncButton(self):
#        " check if the sync languages button should be enabled or not "
#        button = self.checkbutton_sync_languages
#        combo = self.combobox_system_language
#        # no admin user, gray out
#        if self.is_admin == False:
#            button.set_active(False)
#            button.set_sensitive(False)
#            combo.set_sensitive(False)
#            return
#        # admin user, check stuff
#        button.set_sensitive(True)
#        combo.set_sensitive(True)
#        # do not enable the keep the same button if the system has other
#        # users or if the language settings are inconsistent already
#        userlang = self.combobox_user_language.get_active()
#        systemlang = self.combobox_system_language.get_active()
#        if (not self.has_other_users and userlang == systemlang):
#            button.set_active(True)
#        else:
#            button.set_active(False)

    def setupInstallerTreeView(self):
        """ do all the treeview setup here """
        def toggle_cell_func(column, cell, model, iter, data):
            langInfo = model.get_value(iter, LIST_LANG_INFO)

            # check for active and inconsitent 
            inconsistent = langInfo.inconsistent
            #if inconsistent:
            #    print "%s is inconsistent" % langInfo.language

            cell.set_property("active", langInfo.fullInstalled)
            cell.set_property("inconsistent", inconsistent)
            
        def lang_view_func(cell_layout, renderer, model, iter, data):
            langInfo = model.get_value(iter, LIST_LANG_INFO)
            langName = model.get_value(iter, LIST_LANG)
            inconsistent = langInfo.inconsistent
            if (langInfo.changes) :
                markup = "<b>%s</b>" % langName
            else:
                markup = "%s" % langName
            renderer.set_property("markup", markup)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Language"), renderer, text=LIST_LANG)
        column.set_property("expand", True)
        column.set_cell_data_func (renderer, lang_view_func, None)
        self.treeview_languages.append_column(column)

        renderer= Gtk.CellRendererToggle()
        renderer.connect("toggled", self.on_toggled)
        column = Gtk.TreeViewColumn(_("Installed"), renderer)
        column.set_cell_data_func (renderer, toggle_cell_func, None)
        self.treeview_languages.append_column(column)
        # build the store
        self._langlist = Gtk.ListStore(str, gobject.TYPE_PYOBJECT)
        self.treeview_languages.set_model(self._langlist)

    def setupLanguageTreeView(self):
        """ do all the treeview setup here """
        def lang_view_func(cell_layout, renderer, model, iter, data):
            langInfo = model.get_value(iter, LANGTREEVIEW_CODE)
            langName = model.get_value(iter, LANGTREEVIEW_LANGUAGE)
            greyFlag = False
            myiter = model.get_iter_first()
            while myiter:
                str = model.get_value(myiter,LANGTREEVIEW_CODE)
                if str == langInfo: 
                    greyFlag = False
                    break
                if str == "en":
                    greyFlag = True
                    break
                myiter = model.iter_next(myiter)
            if greyFlag:
                markup = "<span foreground=\"grey\">%s</span>" \
                       % self._localeinfo.translate(langInfo, native=True, allCountries=True)
            else:
                markup = "%s" % self._localeinfo.translate(langInfo, native=True, allCountries=True)
            renderer.set_property("markup", markup)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Language"), renderer, text=LANGTREEVIEW_LANGUAGE)
        column.set_property("expand", True)
        column.set_cell_data_func (renderer, lang_view_func, None)
        self.treeview_locales.append_column(column)

        # build the store
        self._language_options = Gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.treeview_locales.set_model(self._language_options)

    def _get_langinfo_on_cursor(self):
        (path, column) = self.treeview_languages.get_cursor()
        if not path:
            return None
        iter = self._langlist.get_iter(path)
        langInfo = self._langlist.get_value(iter, LIST_LANG_INFO)
        return langInfo

    def debug_pkg_status(self):
        langInfo = self._get_langinfo_on_cursor()
        for pkg in langInfo.languagePkgList.items() :
            print ("%s, available: %s, installed: %s, doChange: %s" % (pkg[0], pkg[1].available, pkg[1].installed, pkg[1].doChange))
        print ("inconsistent? : %s" % langInfo.inconsistent)

    def check_status(self):
        changed = False
        countInstall = 0
        countRemove = 0
        for (lang, langInfo) in self._langlist:
            if langInfo.changes:
                changed = True
                for item in langInfo.languagePkgList.values():
                    if item.doChange:
                        if item.installed:
                            countRemove = countRemove + 1
                        else:
                            countInstall = countInstall + 1
        #print "%(INSTALL)d to install, %(REMOVE)d to remove" % (countInstall, countRemove)
        # Translators: %(INSTALL)d is parsed; either keep it exactly as is or remove it entirely, but don't translate "INSTALL".
        textInstall = gettext.ngettext("%(INSTALL)d to install", "%(INSTALL)d to install", countInstall) % {'INSTALL': countInstall}
        # Translators: %(REMOVE)d is parsed; either keep it exactly as is or remove it entirely, but don't translate "REMOVE".
        textRemove = gettext.ngettext("%(REMOVE)d to remove", "%(REMOVE)d to remove", countRemove) % {'REMOVE': countRemove}
        if countRemove == 0 and countInstall == 0: 
            self.label_install_remove.set_text("")
        elif countRemove == 0: 
            self.label_install_remove.set_text(textInstall)
        elif countInstall == 0: 
            self.label_install_remove.set_text(textRemove)
        else: 
            # Translators: this string will concatenate the "%n to install" and "%n to remove" strings, you can replace the comma if you need to.
            self.label_install_remove.set_text(_("%s, %s") % (textInstall, textRemove))
        
        if changed:
            self.button_apply.set_sensitive(True)
        else:
            self.button_apply.set_sensitive(False)

#    @honorBlockedSignals
#    @insensitive
#    def on_combobox_system_language_changed(self, widget):
#        #print "on_combobox_system_language_changed()"
#        if self.writeSystemDefaultLang():
#            # queue a restart of gdm (if it is runing) to make the new
#            # locales usable
#            gdmscript = "/etc/init.d/gdm"
#            if os.path.exists("/var/run/gdm.pid") and os.path.exists(gdmscript):
#                self.runAsRoot(["invoke-rc.d","gdm","reload"])
#        self.updateSystemDefaultCombo()
#        if self.checkbutton_sync_languages.get_active() == True:
#            self.combobox_user_language.set_active(self.combobox_system_language.get_active())
#            self.updateUserDefaultCombo()

#    @honorBlockedSignals
#    @insensitive
#    def on_combobox_user_language_changed(self, widget):
#        #print "on_combobox_user_language_changed()"
#        self.check_input_methods()
#        self.writeUserDefaultLang()
#        self.updateUserDefaultCombo()
#        if self.checkbutton_sync_languages.get_active() == True:
#            self.combobox_system_language.set_active(self.combobox_user_language.get_active())
#            self.updateSystemDefaultCombo()

    @blockSignals
    def check_input_methods(self):
        """ check if the selected langauge has input method support
            and set checkbutton_enable_input_methods accordingly
        """
        if not self.imSwitch.available():
            return
        # get current selected default language
        combo = self.combobox_locale_chooser
        model = combo.get_model()
        if combo.get_active() < 0:
            return
        (lang, code) = model[combo.get_active()]
        #print "Active language: "+code

        combo = self.combobox_input_method
        #cell = combo.get_child().get_cell_renderers()[0]
        # FIXME: use something else than a hardcoded value here
        #cell.set_property("wrap-width",300)
        #cell.set_property("wrap-mode",Pango.WRAP_WORD)
        model = combo.get_model()
        model.clear()

        # find the default
        currentIM = self.imSwitch.getInputMethodForLocale(code)
        if currentIM == None:
            currentIM = 'none'
        #print "Current IM: "+currentIM

        # find out about the other options
        for (i, IM) in enumerate(self.imSwitch.getAvailableInputMethods()):
            iter = model.append()
            model.set_value(iter, IM_CHOICE, IM)
            model.set_value(iter, IM_NAME, IM)
            if IM == currentIM:
                combo.set_active(i)
#        self.check_status()

#    def writeInputMethodConfig(self):
#        """ 
#        write new input method defaults - currently we only support all_ALL
#        """
#        combo = self.combobox_user_language
#        model = combo.get_model()
#        if combo.get_active() < 0:
#            return
#        (lang, code) = model[combo.get_active()]
#        # check if we need to do something
#        new_value = self.checkbutton_enable_input_methods.get_active()
#        if self.imSwitch.enabledForLocale(code) != new_value:
#            if new_value:
#                self.imSwitch.enable(code)
#            else:
#                self.imSwitch.disable(code)
#            #self.showRebootRequired()
#            #self.checkReloginNotification()

#    @honorBlockedSignals
#    def on_checkbutton_enable_input_methods_toggled(self, widget):
#        #print "on_checkbutton_enable_input_methods_toggled()"
#        active = self.checkbutton_enable_input_methods.get_active()
#        self.combo_userlang_dirty = True
#        self.setSensitive(False)
#        self.writeInputMethodConfig()
#        self.setSensitive(True)

#    @honorBlockedSignals
#    def on_checkbutton_sync_languages_toggled(self, widget):
#        #print "on_checkbutton_sync_languages_toggled()"
#        if self.checkbutton_sync_languages.get_active() == True:
#            self.combobox_user_language.set_active(self.combobox_system_language.get_active())
#            self.updateSystemDefaultCombo()
        
    def build_commit_lists(self):
        print self._cache.get_changes()

        try:
            for (lang, langInfo) in self._langlist:
                self._cache.tryChangeDetails(langInfo)
        except ExceptionPkgCacheBroken:
            self.error(
                _("Software database is broken"),
                _("It is impossible to install or remove any software. "
                  "Please use the package manager \"Synaptic\" or run "
                  "\"sudo apt-get install -f\" in a terminal to fix "
                  "this issue at first."))
            sys.exit(1)
        (to_inst, to_rm) = self._cache.getChangesList()
        #print "inst: %s" % to_inst
        #print "rm: %s" % to_rm
        print self._cache.get_changes()
        return (to_inst, to_rm)

    def error(self, summary, msg):
        d = Gtk.MessageDialog(parent=self.window_main,
                              flags=Gtk.DialogFlags.MODAL,
                              type=Gtk.MessageType.ERROR,
                              buttons=Gtk.ButtonsType.CLOSE)
        d.set_markup("<big><b>%s</b></big>\n\n%s" % (summary, msg))
        d.set_title=("")
        res = d.run()
        d.destroy()

    def _show_error_dialog(self, error):
        msg = str(error)
        self.error(msg, "")

    def verify_commit_lists(self, inst_list, rm_list):
        """ verify if the selected package can actually be installed """
        res = True
        try:
            for pkg in inst_list:
                if pkg in self._cache:
                    self._cache[pkg].mark_install()
            for pkg in rm_list:
                if pkg in self._cache:
                    self._cache[pkg].mark_delete()
        except SystemError:
            res = False

        # check if we don't have unexpected changes
        if not self._cache.verify_no_unexpected_changes():
            return False

        # undo the selections
        self._cache.clear()
        if self._cache._depcache.broken_count != 0:
            self.error(_("Could not install the selected language support"),
                       _("This is perhaps a bug of this application. Please "
                         "file a bug report at "
                         "https://bugs.launchpad.net/ubuntu/+source/language-selector/+filebug"))

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
            self.error(
                _("Could not install the full language support"),
                _("Usually this is related to an error in your "
                  "software archive or software manager. Check your "
                  "software preferences in the System > Administration menu."))
            self.setSensitive(True)
            return 0
        #print "inst_list: %s " % inst_list
        #print "rm_list: %s " % rm_list
        self.commit(inst_list, rm_list)

        self.setSensitive(True)
        return len(inst_list)+len(rm_list)

    
    def _run_transaction(self, transaction):
        dia = AptProgressDialog(transaction, parent=self.window_main)
        dia.connect("finished", self._on_finished)
        dia.run()
        
    def _wait_for_aptdaemon_finish(self):
        while not self._transaction_finished:
            while Gtk.events_pending():
                Gtk.main_iteration()
            time.sleep(0.02)

    def _on_finished(self, dialog):
        dialog.hide()
        self._transaction_finished = True

    def update_aptdaemon(self):
        self._transaction_finished = False
        self._update_aptdaemon()
        self._wait_for_aptdaemon_finish()

    @inline_callbacks
    def _update_aptdaemon(self):
        try:
            trans = yield self.ac.update_cache(defer=True)
            self._run_transaction(trans)
        except Exception, e:
            self._show_error_dialog(e)

    def commit_aptdaemon(self, inst, rm):
        self._transaction_finished = False
        self._commit_aptdaemon(inst, rm)
        self._wait_for_aptdaemon_finish()

    @inline_callbacks
    def _commit_aptdaemon(self, inst, rm):
        if len(inst) == 0 and len(rm) == 0:
            return
        try:
            trans = yield self.ac.commit_packages(
                install=inst, reinstall=[], remove=rm, purge=[], upgrade=[],
                downgrade=[], defer=True)
            self._run_transaction(trans)
        except Exception, e:
            self._show_error_dialog(e)

    # we default with update/commit to aptdaemon
    update = update_aptdaemon
    commit = commit_aptdaemon

    def hide_on_delete(self, widget, event):
        return Gtk.Widget.hide_on_delete(widget)

    def verifyInstalledLangPacks(self):
        """ called at the start to inform about possible missing
            langpacks (e.g. gnome/kde langpack transition)
        """
        #print "verifyInstalledLangPacks"
        missing = self.getMissingLangPacks()

        #print "Missing: %s " % missing
        if len(missing) > 0:
            # FIXME: add "details"
            d = Gtk.MessageDialog(parent=self.window_main,
                                  flags=Gtk.DialogFlags.MODAL,
                                  type=Gtk.MessageType.QUESTION)
            d.set_markup("<big><b>%s</b></big>\n\n%s" % (
                _("The language support is not installed completely"),
                _("Some translations or writing aids available for your "
                  "chosen languages are not installed yet. Do you want "
                  "to install them now?")))
            d.add_buttons(_("_Remind Me Later"), Gtk.ResponseType.NO,
                          _("_Install"), Gtk.ResponseType.YES)
            d.set_default_response(Gtk.ResponseType.YES)
            d.set_title("")
            expander = Gtk.Expander.new(_("Details"))
            scroll = Gtk.ScrolledWindow()
            scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            textview = Gtk.TextView()
            textview.set_cursor_visible(False)
            textview.set_editable(False)
            buf = textview.get_buffer()
            pkgs = ""
            for pkg in missing:
                pkgs += "%s\n" % pkg
            buf.set_text(pkgs, -1)
            buf.place_cursor(buf.get_start_iter())
            expander.add(scroll)
            scroll.add(textview)
            d.get_message_area().pack_start(expander, True, True, 0)
            expander.show_all()
            res = d.run()
            d.destroy()
            if res == Gtk.ResponseType.YES:
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
            self.error(
                _("Software database is broken"),
                _("It is impossible to install or remove any software. "
                  "Please use the package manager \"Synaptic\" or run "
                  "\"sudo apt-get install -f\" in a terminal to fix "
                  "this issue at first."))
            sys.exit(1)

        languageList = self._cache.getLanguageInformation()
        #print "ll size: ", len(languageList)
        #print "ll type: ", type(languageList)
        for lang in languageList:
            #print "langInfo: %s (%s)" % (lang.language, lang.languageCode)
            inconsistent = lang.inconsistent
            #if inconsistent:
            #    print "inconsistent", lang.language
            installed = lang.fullInstalled
            lang_name = self._localeinfo.translate(lang.languageCode)
            self._langlist.append([lang_name, lang])
        self._langlist.set_sort_column_id(LIST_LANG, Gtk.SortType.ASCENDING)
        for button in ( 
              "checkbutton_translations",
              "checkbutton_writing_aids",
              "checkbutton_input_methods",
              "checkbutton_fonts"):
            self.block_toggle = True
            getattr(self, button).set_active(False)
            getattr(self, button).set_sensitive(False)
            self.block_toggle = False

    def writeSystemDefaultLang(self):
        combo = self.combobox_locale_chooser
        model = combo.get_model()
        if combo.get_active() < 0:
            return False
        (lang, code) = model[combo.get_active()]
        old_code = self._localeinfo.getSystemDefaultLanguage()[0]
        # no changes, nothing to do
        macr = macros.LangpackMacros(self._datadir, old_code)
        if macr["LOCALE"] == code:
            return False
        self.writeSysLangSetting(sysLang=code)
        return True

    def writeUserDefaultLang(self):
        combo = self.combobox_locale_chooser
        model = combo.get_model()
        if combo.get_active() < 0:
            return
        (lang, code) = model[combo.get_active()]
        temp = self._localeinfo.getUserDefaultLanguage()[0]
        if temp == None:
            old_code = self._localeinfo.getSystemDefaultLanguage()[0]
        else:
            old_code = temp
        # no changes, nothing to do
        macr = macros.LangpackMacros(self._datadir, old_code)
        if macr["LOCALE"] == code:
            return False
        self.writeUserLangSetting(userLang=code)
        return True

    def writeSystemLanguage(self, languageString):
        old_string = self._localeinfo.getSystemDefaultLanguage()[1]
        # no changes, nothing to do
        if old_string == languageString:
            return False
        self.writeSysLanguageSetting(sysLanguage=languageString)
        return True

    def writeUserLanguage(self, languageString):
        temp = self._localeinfo.getUserDefaultLanguage()[1]
        if len(temp) == 0:
            old_string = self._localeinfo.getSystemDefaultLanguage()[1]
        else:
            old_string = temp
        # no changes, nothing to do
        if old_string == languageString:
            return False
        self.writeUserLanguageSetting(userLanguage=languageString)
        return True

    @blockSignals
    def updateLocaleChooserCombo(self):
        #print "updateLocaleChooserCombo()"
        combo = self.combobox_locale_chooser
        #XXX get_cell_renderers does not exist in GTK3
        #cell = combo.get_child().get_cell_renderers()[0]
        # FIXME: use something else than a hardcoded value here
        #cell.set_property("wrap-width",300)
        #cell.set_property("wrap-mode",Pango.WRAP_WORD)
        model = combo.get_model()
        model.clear()

        # find the default
        defaultLangName = None
        (defaultLangCode, languageString) = self._localeinfo.getUserDefaultLanguage()
        if len(defaultLangCode) == 0:
            defaultLangCode = self._localeinfo.getSystemDefaultLanguage()[0]
        if len(defaultLangCode) > 0:
            macr = macros.LangpackMacros(self._datadir, defaultLangCode)
            defaultLangCode = macr["LOCALE"]
            defaultLangName = self._localeinfo.translate(defaultLangCode, native=True)

        # find out about the other options        
        avail_locales = self._localeinfo.generated_locales()

        """ languages for message translation """
        self._language_options.clear()

        # to facilitate lookups: extend the list of available locales with items
        # without country code
        extended_localelist = {}
        for loc in avail_locales:
            lang = re.sub('_[A-Z]+', '', loc)
            for string in loc, lang:
                extended_localelist[string] = 1

        # get the union of /usr/share/locale-langpack and /usr/share/locale
        translation_dirs = {}
        lp_dir = '/usr/share/locale-langpack'
        if os.path.isdir(lp_dir):
            for t_dir in os.listdir(lp_dir):
                translation_dirs[t_dir] = 1
        loc_dir = '/usr/share/locale'
        if os.path.isdir(loc_dir):
            for t_dir in os.listdir(loc_dir):
                translation_dirs[t_dir] = 1

        # get the intersection of available translation_dirs and the extended
        # locale list
        intersection = {}
        for loc in extended_localelist:
            if loc in translation_dirs:
                intersection[loc] = 1

        # If country code items in a language exist:
        # - Remove the item without country code, since gettext won't find a
        #   translation under e.g. 'de_DE' if the first item in LANGUAGE is 'de'
        #   (see https://launchpad.net/bugs/700213). 'en' is kept, though, since
        #   it's always the last item in LANGUAGE per design.
        # - Make sure that the main dialect of the language is represented among
        #   the country code items (see https://launchpad.net/bugs/710148).
        main = {}
        for line in open(os.path.join(self._datadir, 'data', 'main-countries')):
            if re.match('\s*(?:#|$)', line):
                continue
            k, v = line.split()
            main[k] = v
        count = {}
        for lang in intersection:
            if re.match('en[^a-z]', lang):
                continue
            no_country = re.sub('_[A-Z]+', '', lang)
            if no_country in count:
                count[no_country] += 1
            else:
                count[no_country] = 1
        for langcode in count:
            if count[langcode] > 1:
                if langcode in intersection:
                    del intersection[langcode]
                if langcode in main:
                    intersection[ main[langcode] ] = 1

        if len(intersection) == 0:
            intersection['en'] = 1

        # prepare the list for the Language combo box by adding human readable
        # languages and countries, sorting etc.
        mylist = []
        for (i, option) in enumerate( intersection.keys() ):
            mylist.append([self._localeinfo.translate(option, native=True), option])
        if len(languageString) > 0:
            self.userEnvLanguage = languageString
            languages = languageString.split(":")
        else:
            if 'LANGUAGE' in os.environ:
                self.userEnvLanguage = os.environ.get("LANGUAGE")
                languages = self.userEnvLanguage.split(":")
            else:
                self.userEnvLanguage = self._localeinfo.makeEnvString(defaultLangCode)
                languages = self.userEnvLanguage.split(":")
        mylist_sorted = self.bubbleSort(mylist, languages)
        for i in mylist_sorted:
            self._language_options.append(i)

        """ locales for misc. format preferences """
        for (i, locale) in enumerate(avail_locales):
            iter = model.append()
            model.set_value(iter, LANGTREEVIEW_LANGUAGE,
                    self._localeinfo.translate(locale, native=True))
            model.set_value(iter, LANGTREEVIEW_CODE, locale)
            if (defaultLangName and
                   self._localeinfo.translate(locale, native=True) == defaultLangName):
                combo.set_active(i)
        self.updateExampleBox()

    def bubbleSort(self, sortlist, presort=None):
        """
        Sort the list 'sortlist' using bubble sort.
        Optionally, if a list 'presort' is given, put this list first and bubble sort the rest.
        """
        for i in range(0,len(sortlist)-1):
            for j in range(0,len(sortlist)-1):
                data1 = sortlist[j][1]  
                data2 = sortlist[j+1][1]
                try:
                    v1 = presort.index(data1)
                except:
                    v1 = 100000
                try:
                    v2 = presort.index(data2)
                except:
                    v2 = 100000
                if (v1>v2):
                    sortlist[j],sortlist[j+1] = sortlist[j+1], sortlist[j]   
                elif (v1 >= 100000 and v2 >= 100000 and data1 > data2):
                    sortlist[j],sortlist[j+1] = sortlist[j+1], sortlist[j]
        return sortlist

#        # reset the state of the apply button
#        self.combo_syslang_dirty = False
#        self.check_status()

    # FIXME: updateUserDefaultCombo and updateSystemDefaultCombo
    #        duplicate too much code
#    @blockSignals
#    def updateUserDefaultCombo(self):
#        #print "updateUserDefault()"
#        combo = self.combobox_user_language
#        cell = combo.get_child().get_cell_renderers()[0]
#        # FIXME: use something else than a hardcoded value here
#        cell.set_property("wrap-width",300)
#        cell.set_property("wrap-mode",Pango.WRAP_WORD)
#        model = combo.get_model()
#        model.clear()

#        # find the default
#        defaultLangName = None
#        defaultLangCode = self.getUserDefaultLanguage()
#        if defaultLangCode == None:
#            defaultLangCode = self.getSystemDefaultLanguage()
#        if defaultLangCode:
#            defaultLangName = self._localeinfo.translate(defaultLangCode)

#        # find out about the other options        
#        for (i, locale) in enumerate(self._localeinfo.generated_locales()):
#            iter = model.append()
#            model.set(iter,
#                      COMBO_LANGUAGE,self._localeinfo.translate(locale),
#                      COMBO_CODE, locale)
#            if (defaultLangName and 
#                   self._localeinfo.translate(locale) == defaultLangName):
#                combo.set_active(i)
#            
#        # reset the state of the apply button
#        self.combo_userlang_dirty = False
#        self.check_status()

    def updateExampleBox(self):
        combo = self.combobox_locale_chooser
        model = combo.get_model()
        if combo.get_active() < 0:
            return
        (lang, code) = model[combo.get_active()]
        macr = macros.LangpackMacros(self._datadir, code)
        mylocale = macr["SYSLOCALE"]
        try:
            locale.setlocale(locale.LC_ALL, mylocale)
            self.label_example_currency.set_text(locale.currency(20457.99))
            self.label_example_number.set_text(locale.format("%.2f", 1234567.89, grouping=True))
            self.label_example_date.set_text(time.strftime(locale.nl_langinfo(locale.D_T_FMT)))
        except locale.Error as detail:
            self.label_example_number.set_text('[ '
            + _("Failed to apply the '%s' format choice:") % mylocale + "\n%s ]" % detail)


    ####################################################
    # window_installer signal handlers                 #
    ####################################################
    def on_treeview_languages_cursor_changed(self, treeview):
        #print "on_treeview_languages_cursor_changed()"
        langInfo = self._get_langinfo_on_cursor()
        for (button, attr) in ( 
              ("checkbutton_translations", langInfo.languagePkgList["languagePack"]),
              ("checkbutton_writing_aids", langInfo.languagePkgList["languageSupportWritingAids"]),
              ("checkbutton_input_methods", langInfo.languagePkgList["languageSupportInputMethods"]),
              ("checkbutton_fonts", langInfo.languagePkgList["languageSupportFonts"])  ):
            self.block_toggle = True
            if ((attr.installed and not attr.doChange) or (not attr.installed and attr.doChange)) :
                getattr(self, button).set_active(True)
            else :
                getattr(self, button).set_active(False)
            getattr(self, button).set_sensitive(attr.available)
            self.block_toggle = False
            #self.debug_pkg_status()

    def on_treeview_languages_row_activated(self, treeview, path, view_column):
        self.on_toggled(None,str(path[0]))

    # details checkboxes
    def on_checkbutton_fonts_clicked(self, button):
        if self.block_toggle: return
        langInfo = self._get_langinfo_on_cursor()
        langInfo.languagePkgList["languageSupportFonts"].doChange = not langInfo.languagePkgList["languageSupportFonts"].doChange
        self.check_status()
        self.treeview_languages.queue_draw()
        #self.debug_pkg_status()
    def on_checkbutton_input_methods_clicked(self, button):
        if self.block_toggle: return
        langInfo = self._get_langinfo_on_cursor()
        langInfo.languagePkgList["languageSupportInputMethods"].doChange = not langInfo.languagePkgList["languageSupportInputMethods"].doChange
        self.check_status()
        self.treeview_languages.queue_draw()
        #self.debug_pkg_status()
    def on_checkbutton_writing_aids_clicked(self, button):
        if self.block_toggle: return
        langInfo = self._get_langinfo_on_cursor()
        langInfo.languagePkgList["languageSupportWritingAids"].doChange = not langInfo.languagePkgList["languageSupportWritingAids"].doChange
        self.check_status()
        self.treeview_languages.queue_draw()
        #self.debug_pkg_status()
    def on_checkbutton_translations_clicked(self, button):
        if self.block_toggle: return
        langInfo = self._get_langinfo_on_cursor()
        langInfo.languagePkgList["languagePack"].doChange = not langInfo.languagePkgList["languagePack"].doChange
        self.check_status()
        self.treeview_languages.queue_draw()
        #self.debug_pkg_status()

    # the global toggle
    def on_toggled(self, renderer, path_string):
        """ called when on install toggle """
        iter = self._langlist.get_iter_from_string(path_string)
        langInfo = self._langlist.get_value(iter, LIST_LANG_INFO)

        # special handling for inconsistent state
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

        self.check_status()
        self.treeview_languages.queue_draw()
        #self.debug_pkg_status()

    def on_button_cancel_clicked(self, widget):
        #print "button_cancel"
        self.window_installer.hide()

    def on_button_apply_clicked(self, widget):
        self.window_installer.hide()
        if self.commitAllChanges() > 0:
            self.updateLanguageView()
        self.updateLocaleChooserCombo()
        #self.updateSystemDefaultCombo()

    ####################################################
    # window_main signal handlers                      #
    ####################################################
    def on_delete_event(self, event, data):
        if self.window_main.get_property("sensitive") is False:
            return True
        else:
            Gtk.main_quit()

    def on_button_quit_clicked(self, widget):
        Gtk.main_quit()

    @honorBlockedSignals
    def on_window_main_key_press_event(self, widget, event):
        keyname = Gdk.keyval_name(event.keyval)
        if (event.get_state() & Gdk.EventMask.CONTROL_MASK):
            if (keyname == "w"):
                Gtk.main_quit()
        return None

    ####################################################
    # window_main signal handlers (Language tab)       #
    ####################################################
#    @honorBlockedSignals
#    def on_treeview_locales_drag_failed(self, widget):
#        return None

#    @honorBlockedSignals
#    def on_treeview_locales_drag_begin(self, widget):
#        return None

#    @honorBlockedSignals
#    def on_treeview_locales_drag_drop(self, widget):
#        return None

    @honorBlockedSignals
    def on_treeview_locales_drag_end(self, widget, drag_content):
        #print ("on_treeview_locales_drag_end")
        model = widget.get_model()
        myiter = model.get_iter_first()
        envLanguage = ""
        while myiter:   
            str = model.get_value(myiter,LANGTREEVIEW_CODE)
            if (envLanguage != ""):
                envLanguage = envLanguage + ":"
            envLanguage = envLanguage + str
            if str == "en":
                break
            myiter = model.iter_next(myiter)
        #print (envLanguage)
        self.writeUserLanguage(envLanguage)
        self.userEnvLanguage = envLanguage
        #os.environ["LANGUAGE"]=envLanguage

#    @honorBlockedSignals
#    def on_treeview_locales_drag_leave(self, widget):
#        return None

#    @honorBlockedSignals
#    def on_treeview_locales_drag_data_received(self, widget):
#        return None

    @honorBlockedSignals
    @insensitive
    def on_button_apply_system_wide_languages_clicked(self, widget):
        self.writeSystemLanguage(self.userEnvLanguage)
        return None

    def on_button_install_remove_languages_clicked(self, widget):
        self.window_installer.show()

    @honorBlockedSignals
    def on_combobox_input_method_changed(self, widget):
        combo = self.combobox_locale_chooser
        model = combo.get_model()
        if combo.get_active() < 0:
            return
        (lang, code) = model[combo.get_active()]

        combo = self.combobox_input_method
        model = combo.get_model()
        if combo.get_active() < 0:
            return
        (IM_choice, IM_name) = model[combo.get_active()]
        #print "IM: "+IM_choice+"\t"+code
        self.imSwitch.setInputMethodForLocale(IM_choice, code)

    
    ####################################################
    # window_main signal handlers (Text tab)           #
    ####################################################
    @honorBlockedSignals
    @insensitive
    def on_combobox_locale_chooser_changed(self, widget):
        self.check_input_methods()
        self.writeUserDefaultLang()
        self.updateLocaleChooserCombo()
        self.updateExampleBox()

    @honorBlockedSignals
    @insensitive
    def on_button_apply_system_wide_locale_clicked(self, widget):
        self.writeSystemDefaultLang()
        return None

