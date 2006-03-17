# LoclaeInfo.py (c) 2006 Canonical, released under the GPL
#
# a helper class to get locale info

import string
import subprocess

from gettext import gettext as _

class LocaleInfo(object):
    " class with handy functions to parse the locale information "
    
    environment = "/etc/environment"
    def __init__(self, lang_file, country_file, languagelist_file):
        self._lang = {}
        self._country = {}
        self._languagelist = {}
        # read lang file
        self._langFile = lang_file
        for line in open(lang_file):
            tmp = line.strip()
            if tmp.startswith("#") or tmp == "":
                continue
            (code, lang) = tmp.split(":")
            self._lang[code] = lang
        # read countries
        for line in open(country_file):
            tmp = line.strip()
            if tmp.startswith("#") or tmp == "":
                continue
            (un, code, long_code, descr, cap) = tmp.split(":")
            self._country[code] = descr
        # read the languagelist
        for line in open(languagelist_file):
            tmp = line.strip()
            if tmp.startswith("#") or tmp == "":
                continue
            w = tmp.split(";")
            localeenv = w[6].split(":")
            #print localeenv
            self._languagelist[localeenv[0]] = '%s' % w[6]

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
            (runing locale -a) """
        locales = []
        p = subprocess.Popen(["locale", "-a"], stdout=subprocess.PIPE)
        for line in p.stdout.readlines():
            tmp = line.strip()
            if tmp.startswith("#") or tmp == "" or tmp == "C" or tmp == "POSIX":
                continue
            # we are only interessted in the locale, not the codec
            locale = string.split(tmp)[0]
            locale = string.split(locale,".")[0]
            locale = string.split(locale,"@")[0]
            if not locale in locales:
                locales.append(locale)
        #print locales
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
        # first check if we got somethign from languagelist
        if self._languagelist.has_key(code):
            return self._languagelist[code]
        # if not, fall back to "dumb" behaviour
        if not "_" in code:
            return code
        (lang, region) = string.split(code, "_")
        return "%s:%s" % (code, lang)

    def getDefaultLanguage(self):
        """ returns the current default language (e.g. zh_CN) """
        for line in open(self.environment).readlines():
            line = line.strip()
            if line.startswith("LANGUAGE="):
                (key,value) = line.split("=")
                value = value.strip('"')
                return value.split(":")[0]

if __name__ == "__main__":
    datadir = "/usr/share/language-selector/"
    li = LocaleInfo("%s/data/languages" % datadir,
                    "%s/data/countries" % datadir,
                    "%s/data/languagelist" % datadir)

    print li.getDefaultLanguage()
