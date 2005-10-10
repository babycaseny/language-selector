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
import apt, apt_pkg
import os.path
import shutil
import subprocess
import thread
import time
import gettext
import sys

def _(s): return gettext.gettext(s)
 
(LIST_LANG,                     # language (i18n/human-readable)
 LIST_TRANSLATION,              # does the user want the translation pkgs
 LIST_TRANSLATION_AVAILABLE,    # are the translation pkgs available at all?
 LIST_INPUT,                    # does the user want the input-aids pkgs
 LIST_INPUT_AVAILABLE,          # are the input aids available at all?
 LIST_LANG_CODE                 # the short country code (e.g. de, pt_BR)
 ) = range(6)

(COMBO_LANGUAGE,
 COMBO_CODE) = range(2)

from GladeApp import GladeApp

class LocaleInfo(object):
    " class with handy functions to parse the locale information "
    
    def __init__(self, lang_file, country_file):
        self._lang = {}
        self._country = {}
        # read lang file
        self._langFile = lang_file
        for line in open(lang_file):
            tmp = string.strip(line)
            if tmp.startswith("#") or tmp == "":
                continue
            (code, lang) = string.split(tmp,":")
            self._lang[code] = lang
        # read countries
        for line in open(country_file):
            tmp = string.strip(line)
            if tmp.startswith("#") or tmp == "":
                continue
            (un, code, long_code, descr, cap) = string.split(tmp,":")
            self._country[code] = descr

    def lang(self, code):
        """ map language code to language name """
        if self._lang.has_key(code):
            return self._lang[code]
        return ""

    def country(self, code):
        """ map country code to country name"""
        if self._country.has_key(code):
            return self._country[code]
        return ""

    def generated_locales(self):
        """ return a list of locales avaialble on the system
            (reading /etc/locales.gen) """
        locales = []
        for line in open("/etc/locale.gen"):
            tmp = string.strip(line)
            if tmp.startswith("#") or tmp == "":
                continue
            # we are only interessted in the locale, not the codec
            locale = string.split(tmp)[0]
            locale = string.split(locale,".")[0]
            locale = string.split(locale,"@")[0]
            if not locale in locales:
                locales.append(locale)
        return locales

    def translate(self, locale):
        """ get a locale code and output a human readable name """
        # sanity check, make other code easier
        if "_" in locale:
            (lang, country) = string.split(locale, "_")
            ret = "%s (%s) " % (_(self.lang(lang)), _(self.country(country)))
        else:
            ret = self.lang(locale)
        return ret

    def makeEnvString(self, code):
        """ input is a language code, output a string that can be put in
            the LANGUAGE enviroment variable.
            E.g: en_DK -> en_DK:en
        """
        if not "_" in code:
            return code
        (lang, region) = string.split(code, "_")
        return "%s:%s" % (code, lang)
            

class GtkProgress(apt.OpProgress):
    def __init__(self, progressbar):
        self._progressbar = progressbar
    def Update(self, percent):
        #print percent
        #print self.Op
        #print self.SubOp
        self._progressbar.set_text(self.op)
        self._progressbar.set_fraction(percent/100.0)
        while gtk.events_pending():
            gtk.main_iteration()

class LanguageSelector(GladeApp):

    # those packages are used to figure if kde/gnome is installed
    kde_detect_pkg = "kdelibs4c2"
    gnome_detect_pkg = "libgnome2-0"
    
    def __init__(self, datadir=""):
        GladeApp.__init__(self, datadir=datadir)

        #build the combobox (with model)
        combo = self._glade.get_widget("combobox_default_lang")
        model = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        cell = gtk.CellRendererText()
        combo.pack_start(cell, True)
        combo.add_attribute(cell, 'text', COMBO_LANGUAGE)
        combo.set_model(model)
        combo.connect("changed", self.combo_changed)
        self.combo_dirty = False

        # apply button
        self._button_ok = self._glade.get_widget("button_ok")
        self._button_ok.set_sensitive(False)

        # build the treeview
        self._treeview = self._glade.get_widget("treeview_languages")
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(_("Language"), renderer, text=LIST_LANG)
        column.set_property("expand", True)
        self._treeview.append_column(column)
        renderer= gtk.CellRendererToggle()
        renderer.connect("toggled", self.toggled, LIST_TRANSLATION)
        column = gtk.TreeViewColumn(_("Translations"), renderer,
                                    active=LIST_TRANSLATION,
                                    activatable=LIST_TRANSLATION_AVAILABLE,
                                    sensitive=LIST_TRANSLATION_AVAILABLE,
                                    visible=LIST_TRANSLATION_AVAILABLE)
        
        self._treeview.append_column(column)
        renderer= gtk.CellRendererToggle()
        renderer.connect("toggled", self.toggled, LIST_INPUT)
        column = gtk.TreeViewColumn(_("Writing Aids"), renderer,
                                    active=LIST_INPUT,
                                    activatable=LIST_INPUT_AVAILABLE,
                                    sensitive=LIST_INPUT_AVAILABLE,
                                    visible=LIST_INPUT_AVAILABLE)
                                    
        self._treeview.append_column(column)
        # build the store
        self._langlist = gtk.ListStore(str, bool, bool, bool, bool, str)
        self._treeview.set_model(self._langlist)
        self._win.show()
        
        # load the localeinfo "database"
        self._localeinfo = LocaleInfo("%s/languages" % self._datadir,
                                      "%s/countries" % self._datadir)
        self.updateLanguageView()
        self.updateSystemDefaultCombo()
        # see if something is missing
        self.verifyInstalledLangPacks()

    def check_apply_button(self):
        (inst_list, rm_list) = self.build_commit_lists()
        if self.combo_dirty or len(inst_list) > 0 or len(rm_list) > 0:
            self._button_ok.set_sensitive(True)
        else:
            self._button_ok.set_sensitive(False)

    def combo_changed(self, widget):
        self.combo_dirty = True
        self.check_apply_button()

    def verifyInstalledLangPacks(self):
        """ called at the start to inform about possible missing
            langpacks (e.g. gnome/kde langpack transition)
        """
        missing = []
        for (lang, trans, has_trans, input, has_inp, code) in self._langlist:
            trans_package = "language-pack-%s" % code
            # we have a langpack installed, see if we have all of it
            if self._cache.has_key(trans_package) and \
               self._cache[trans_package].isInstalled:
                #print "IsInstalled: %s " % trans_package
                if self._cache.has_key(self.kde_detect_pkg) and \
                   self._cache[self.kde_detect_pkg].isInstalled and \
                   self._cache.has_key("language-pack-kde-%s" % code) and \
                   not self._cache["language-pack-kde-%s" % code].isInstalled:
                    missing.append("language-pack-kde-%s" % code)
                if self._cache.has_key(self.gnome_detect_pkg) and \
                   self._cache[self.gnome_detect_pkg].isInstalled and \
                   self._cache.has_key("language-pack-gnome-%s"%code) and \
                   not self._cache["language-pack-gnome-%s"%code].isInstalled:
                    missing.append("language-pack-gnome-%s" % code)

        #print "Missing: %s " % missing
        if len(missing) > 0:
            d = gtk.MessageDialog(parent=self._win,
                                  flags=gtk.DIALOG_MODAL,
                                  type=gtk.MESSAGE_QUESTION)
            d.set_markup("<big><b>%s</b></big>\n\n%s" % (
                _("Update language support?"),
                _("Some packages for full language support "
                  "are not installed on your system. Do you "
                  "want to install them now?")))
            d.add_buttons(_("Remind me again"), gtk.RESPONSE_NO,
                          _("Install now"), gtk.RESPONSE_YES)
            d.set_default_response(gtk.RESPONSE_YES)
            res = d.run()
            d.destroy()
            if res == gtk.RESPONSE_YES:
                self.commit(missing, [])


    def toggled(self, renderer, path_string, what):
        iter = self._langlist.get_iter_from_string(path_string)
        old = self._langlist.get_value(iter, what)
        self._langlist.set_value(iter, what, not old)
        self.check_apply_button()

    def build_commit_lists(self):
        inst_list = []
        rm_list = []
        
        for (lang, trans, has_trans, input, has_inp, code) in self._langlist:
            # see what translation packages we will need
            trans_packages = ["language-pack-%s" % code]
            if self._cache.has_key(self.kde_detect_pkg) and \
               self._cache[self.kde_detect_pkg].isInstalled:
                trans_packages.append("language-pack-kde-%s" % code)
            if self._cache.has_key(self.gnome_detect_pkg) and \
               self._cache[self.gnome_detect_pkg].isInstalled:
                trans_packages.append("language-pack-gnome-%s" % code)

            # see what needs to be installed/removed
            if has_trans and trans != self._cache["language-pack-%s" % code].isInstalled:
                if trans:
                    inst_list.extend(trans_packages)
                else:
                    rm_list.extend(trans_packages)
                    
            if has_inp and input != self._cache["language-support-%s" % code].isInstalled:
                if input:
                    inst_list.append("language-support-%s" % code)
                else:
                    rm_list.append("language-support-%s" % code)

        return (inst_list, rm_list)

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
        for pkg in self._cache.keys():
            self._cache[pkg].markKeep()
        assert self._cache._depcache.BrokenCount == 0
        return res

    def on_button_ok_clicked(self, widget):
        #print "button_ok"
        (inst_list, rm_list) = self.build_commit_lists()
        if not self.verify_commit_lists(inst_list, rm_list):
            d = gtk.MessageDialog(parent=self._win,
                                  flags=gtk.DIALOG_MODAL,
                                  type=gtk.MESSAGE_INFO,
                                  buttons=gtk.BUTTONS_OK)
            d.set_markup("<big><b>%s</b></big>\n\n%s" % (
                _("Can not apply changes"),
                _("Some packages for full language support "
                  "can't be installed on your system. This usually "
                  "means there is something wrong in the ubuntu archive "
                  "or with your 'apt' software settings.")))
            res = d.run()
            d.destroy()
            return
        #print "inst_list: %s " % inst_list
        #print "rm_list: %s " % rm_list
        self.commit(inst_list, rm_list)
        self.writeSystemDefaultLang()
        #gtk.main_quit()
        self.updateLanguageView()
        self.updateSystemDefaultCombo()

    def run_synaptic(self, lock, inst, rm):
        cmd = ["/usr/sbin/synaptic", "--hide-main-window",
               "--non-interactive", "--set-selections",
               "--finish-str", _("The list of available languages on the "
                                 "system has been updated.")
               ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        f = proc.stdin
        for s in inst:
            f.write("%s\tinstall\n" % s)
        for s in rm:
            f.write("%s\tdeinstall\n" % s)
        f.close()
        proc.wait()
        # queue a restart of gdm (if it is runing) to make the new
        # locales usable
        gdmscript = "/etc/init.d/gdm"
        if os.path.exists("/var/run/gdm.pid") and os.path.exists(gdmscript):
            subprocess.call(["invoke-rc.d","gdm","reload"])
        lock.release()

    def commit(self, inst, rm):
        # unlock here to make sure that lock/unlock are always run
        # pair-wise
        apt_pkg.PkgSystemUnLock()

        if len(inst) == 0 and len(rm) == 0:
            return
        self._win.set_sensitive(False)
        lock = thread.allocate_lock()
        lock.acquire()
        t = thread.start_new_thread(self.run_synaptic,(lock,inst,rm))
        while lock.locked():
            while gtk.events_pending():
                gtk.main_iteration()
            time.sleep(0.05)
        self._win.set_sensitive(True)
        while gtk.events_pending():
            gtk.main_iteration()
                    
    def on_button_cancel_clicked(self, widget):
        #print "button_cancel"
        gtk.main_quit()

    def on_delete_event(self, event, data):
        #print "delete_event"
        gtk.main_quit()

    def updateLanguageView(self):
        #print "updateLanguageView()"

        # get the lock
        try:
            apt_pkg.PkgSystemLock()
        except SystemError:
            d = gtk.MessageDialog(parent=self._win,
                                  flags=gtk.DIALOG_MODAL,
                                  type=gtk.MESSAGE_ERROR,
                                  buttons=gtk.BUTTONS_OK)
            d.set_markup("<big><b>%s</b></big>\n\n%s" % (
                _("Unable to get exclusive lock"),
                _("This usually means that another package management "
                  "application (like apt-get or aptitude) already running. "
                  "Please close that application first")))
            res = d.run()
            d.destroy()
            sys.exit()

        self._langlist.clear()
        self._glade.get_widget("hbox_status").show()
        progress = GtkProgress(self._glade.get_widget("progressbar_cache"))
        self._cache = apt.Cache(progress)
        self._glade.get_widget("hbox_status").hide()
        for line in open(self._localeinfo._langFile):
            tmp = string.strip(line)
            if tmp.startswith("#"):
                continue
            (code, lang) = tmp.split(":")
            trans = None
            inp = None
            has_translation = self._cache.has_key("language-pack-%s" % code)
            has_input = self._cache.has_key("language-support-%s" % code)
            if has_translation:
                trans = self._cache["language-pack-%s" % code].isInstalled
            if  has_input:
                inp = self._cache["language-support-%s" % code].isInstalled
            if has_input or has_translation:
                self._langlist.append([_(lang),
                                       trans, has_translation,
                                       inp, has_input,
                                       code])
        self._langlist.set_sort_column_id(LIST_LANG, gtk.SORT_ASCENDING)

    def writeSystemDefaultLang(self):
        combo = self._glade.get_widget("combobox_default_lang")
        model = combo.get_model()
        (lang, code) = model[combo.get_active()]
        #print "lang=%s, code=%s" % (lang, code)

        # make a copy (in case we do anything bad)
        if os.path.exists("/etc/enviroment"):
            shutil.copy("/etc/environment", "/etc/environment.save")
        out = open("/etc/environment.new","w+")
        foundLanguage = False  # the LANGUAGE var
        foundLang = False      # the LANG var
        if os.path.exists("/etc/environment"):
            for line in open("/etc/environment"):
                tmp = string.strip(line)
                if tmp.startswith("LANGUAGE="):
                    foundLanguage = True
                    line="LANGUAGE=\"%s\"\n" % self._localeinfo.makeEnvString(code)
                    #print line
                if tmp.startswith("LANG="):
                    foundLang = True
                    # we always write utf8 languages
                    line="LANG=\"%s.UTF-8\"\n" % code
                out.write(line)
                #print line
        if foundLanguage == False:
            line="LANGUAGE=\"%s\"\n" % self._localeinfo.makeEnvString(code)
            out.write(line)
        if foundLang == False:
            line="LANG=\"%s.UTF-8\"\n" % code
            out.write(line)
        shutil.move("/etc/environment.new", "/etc/environment")
        
    def updateSystemDefaultCombo(self):
        #print "updateSystemDefault()"
        combo = self._glade.get_widget("combobox_default_lang")
        cell = combo.get_child().get_cell_renderers()[0]
        # FIXME: use something else than a hardcoded value here
        cell.set_property("wrap-width",300)
        cell.set_property("wrap-mode",pango.WRAP_WORD)
        model = combo.get_model()
        model.clear()

        # find out about the other options        
        for locale in self._localeinfo.generated_locales():
            iter = model.append()
            model.set(iter,
                      COMBO_LANGUAGE,self._localeinfo.translate(locale),
                      COMBO_CODE, locale)
            #combo.append_text(self._localeinfo.translate(locale))
        # find the default
        if not os.path.exists("/etc/environment"):
            combo.set_active(0)
            return
        for line in open("/etc/environment"):
            tmp = string.strip(line)
            l = "LANGUAGE="
            if tmp.startswith(l):
                tmp = tmp[len(l):]
                langs = string.strip(tmp, "\"").split(":")
                # check if LANGUAGE is empty
                info = self._localeinfo.translate(langs.pop(0))
                i=0
                for s in model:
                    if s[0] == info:
                        combo.set_active(i)
                        break
                    i += 1
        # reset the state of the apply button
        self.combo_dirty = False
        self.check_apply_button()
