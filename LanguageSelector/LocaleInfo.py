# LoclaeInfo.py (c) 2006 Canonical, released under the GPL
#
# a helper class to get locale info

import string
import re            
import subprocess
import gettext
import os.path

from gettext import gettext as _
from xml.etree.ElementTree import ElementTree

class LocaleInfo(object):
    " class with handy functions to parse the locale information "
    
    environments = ["/etc/default/locale", "/etc/environment"]
    def __init__(self, languagelist_file):
        # map language to human readable name, e.g.:
        # "pt"->"Portugise", "de"->"German", "en"->"English"
        self._lang = {}

        # map country to human readable name, e.g.:
        # "BR"->"Brasil", "DE"->"Germany", "US"->"United States"
        self._country = {}
        
        # map locale (language+country) to the LANGUAGE environment, e.g.:
        # "pt_PT"->"pt_PT:pt:pt_BR:en_GB:en"
        self._languagelist = {}
        
        # read lang file (we don't use iso_639_3 as it does crash there with:
        # xml.parsers.expat.ExpatError: not well-formed (invalid token): line 52, column 11
        et = ElementTree(file="/usr/share/xml/iso-codes/iso_639.xml")
        it = et.getiterator('iso_639_entry')
        for elm in it:
            lang = elm.attrib["name"]
            if elm.attrib.has_key("iso_639_1_code"):
                code = elm.attrib["iso_639_1_code"]
            else:
                code = elm.attrib["iso_639_2T_code"]
            self._lang[code] = gettext.dgettext('iso_639', lang)
            
        # read countries
        et = ElementTree(file="/usr/share/xml/iso-codes/iso_3166.xml")
        it = et.getiterator('iso_3166_entry')
        for elm in it:
            if elm.attrib.has_key("common_name"):
                descr = elm.attrib["common_name"]
            else:
                descr = elm.attrib["name"]
            if elm.attrib.has_key("alpha_2_code"):
                code = elm.attrib["alpha_2_code"]
            else:
                code = elm.attrib["alpha_3_code"]
            self._country[code] = gettext.dgettext('iso_3166',descr)
            
        # read the languagelist
        for line in open(languagelist_file):
            tmp = line.strip()
            if tmp.startswith("#") or tmp == "":
                continue
            w = tmp.split(";")
            # FIXME: the latest localechoosers "languagelist" does
            # no longer have this field for most languages, so
            # deal with it and don't set LANGUAGE then
            # - the interessting question is what to do
            # if LANGUAGE is already set and the new
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
        for line in string.split(p.communicate()[0], "\n"):
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
        if "_" in locale:
            (lang, country) = string.split(locale, "_")
            # get all locales for this language
            l = filter(lambda k: k.startswith(lang+"_"), self.generated_locales())
            # only show region/country if we have more than one 
            if len(l) > 1:
                mycountry = self.country(country)
                if mycountry:
                    return "%s (%s)" % (_(self.lang(lang)), _(mycountry))
                else:
                    return "%s" % (_(self.lang(lang)))
            else:
                return _(self.lang(lang))
        return _(self.lang(locale))

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
        for environment in self.environments:
            if not os.path.exists(environment):
                continue
            for line in open(environment).readlines():
                line = line.strip()
                if line.startswith("LANGUAGE="):
                    (key,value) = line.split("=")
                    value = value.strip('"')
                    return value.split(":")[0]
            for line in open(environment).readlines():
                match = re.match(r'LANG="([a-zA-Z_]*).*"$',line)
                if match:
                    return match.group(1)
        return None

if __name__ == "__main__":
    datadir = "/usr/share/language-selector/"
    li = LocaleInfo("%s/data/languages" % datadir,
                    "%s/data/countries" % datadir,
                    "%s/data/languagelist" % datadir)

    print "default: '%s'" % li.getDefaultLanguage()

    print li._lang
    print li._country
    print li._languagelist
    print li.generated_locales()
