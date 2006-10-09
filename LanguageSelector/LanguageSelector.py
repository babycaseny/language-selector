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
import re

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
        conffiles = ["/etc/default/locale", "/etc/environment"]
        for fname in conffiles:
            if os.path.exists(fname):
                for line in open(fname):
                    match = re.match(r'LANG="(.*)"$',line)
                    if match:
                        if "." in match.group(1):
                            return match.group(1).split(".")[0]
                        else:
                            return match.group(1)
        return None

    def setSystemDefaultLanguage(self, defaultLanguageCode):
        " this updates the system default language "
        conffiles = ["/etc/default/locale", "/etc/environment"]
        for fname in conffiles:
            out = open(fname+".new","w+")
            foundLanguage = False  # the LANGUAGE var
            foundLang = False      # the LANG var
            if os.path.exists(fname):
                # look for the line
                for line in open(fname):
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
            # if we have not found them add them
            if foundLanguage == False:
                line="LANGUAGE=\"%s\"\n" % self._localeinfo.makeEnvString(defaultLanguageCode)
                out.write(line)
            if foundLang == False:
                line="LANG=\"%s.UTF-8\"\n" % defaultLanguageCode
                out.write(line)
            out.close()
            shutil.move(fname+".new", fname)

        # now set the fontconfig-voodoo
        fc = FontConfig.FontConfigHack()
        #print defaultLanguageCode
        #print fc.getAvailableConfigs()
        if defaultLanguageCode in fc.getAvailableConfigs():
            fc.setConfig(defaultLanguageCode)
        else:
            fc.removeConfig()
