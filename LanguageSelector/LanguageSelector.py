# (c) 2006 Canonical
# Author: Michael Vogt <michael.vogt@ubuntu.com>
#
# Released under the GPL
#

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
import string

import FontConfig
from gettext import gettext as _
from LocaleInfo import LocaleInfo

from LangCache import *                


# the language-selector abstraction
class LanguageSelectorBase(object):
    """ base class for language-selector code """
    def __init__(self, datadir=""):
        self._datadir = datadir
        # load the localeinfo "database"
        self._localeinfo = LocaleInfo("%s/data/languages" % self._datadir,
                                      "%s/data/countries" % self._datadir,
                                      "%s/data/languagelist" % self._datadir)
        self._cache = None

    def openCache(self, progress):
        self._cache = LanguageSelectorPkgCache(self._localeinfo, progress)

    def getSystemDefaultLanguage(self):
        if not os.path.exists("/etc/environment"):
            return None
        for line in open("/etc/environment"):
            tmp = string.strip(line)
            l = "LANGUAGE="
            if tmp.startswith(l):
                tmp = tmp[len(l):]
                langs = tmp.strip("\"").split(":")
                # check if LANGUAGE is empty
                if len(langs) > 0:
                    return langs[0]
        return None

    def setSystemDefaultLanguage(self, defaultLanguageCode):
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
                    line="LANGUAGE=\"%s\"\n" % self._localeinfo.makeEnvString(defaultLanguageCode)
                    #print line
                if tmp.startswith("LANG="):
                    foundLang = True
                    # we always write utf8 languages
                    line="LANG=\"%s.UTF-8\"\n" % defaultLanguageCode
                out.write(line)
                #print line
        if foundLanguage == False:
            line="LANGUAGE=\"%s\"\n" % self._localeinfo.makeEnvString(defaultLanguageCode)
            out.write(line)
        if foundLang == False:
            line="LANG=\"%s.UTF-8\"\n" % defaultLanguageCode
            out.write(line)
        shutil.move("/etc/environment.new", "/etc/environment")

        # now set the fontconfig-voodoo
        fc = FontConfig.FontConfigHack()
        #print defaultLanguageCode
        #print fc.getAvailableConfigs()
        if defaultLanguageCode in fc.getAvailableConfigs():
            fc.setConfig(defaultLanguageCode)
        else:
            fc.setConfig("none")
