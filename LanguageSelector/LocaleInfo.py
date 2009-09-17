# LoclaeInfo.py (c) 2006 Canonical, released under the GPL
#
# a helper class to get locale info

import string
import re            
import subprocess
import gettext
import os.path
import macros

from gettext import gettext as _
from xml.etree.ElementTree import ElementTree

class LocaleInfo(object):
    " class with handy functions to parse the locale information "
    
    environments = ["/etc/default/locale", "/etc/environment"]
    def __init__(self, languagelist_file):
        # map language to human readable name, e.g.:
        # "pt"->"Portuguise", "de"->"German", "en"->"English"
        self._lang = {}

        # map country to human readable name, e.g.:
        # "BR"->"Brasil", "DE"->"Germany", "US"->"United States"
        self._country = {}
        
        # map locale (language+country) to the LANGUAGE environment, e.g.:
        # "pt_PT"->"pt_PT:pt:pt_BR:en_GB:en"
        self._languagelist = {}
        
        # read lang file
        et = ElementTree(file="/usr/share/xml/iso-codes/iso_639.xml")
        it = et.getiterator('iso_639_entry')
        for elm in it:
            lang = elm.attrib["name"]
            if "iso_639_1_code" in elm.attrib:
                code = elm.attrib["iso_639_1_code"]
            else:
                code = elm.attrib["iso_639_2T_code"]
            if not code in self._lang:
                self._lang[code] = lang
        # Hack for Chinese langpack split
        # Translators: please translate 'Chinese (simplified)' and 'Chinese (traditional)' so that they appear next to each other when sorted alphabetically.
        self._lang['zh-hans'] = _("Chinese (simplified)")
        # Translators: please translate 'Chinese (simplified)' and 'Chinese (traditional)' so that they appear next to each other when sorted alphabetically.
        self._lang['zh-hant'] = _("Chinese (traditional)")
        # end hack
        et = ElementTree(file="/usr/share/xml/iso-codes/iso_639_3.xml")
        it = et.getiterator('iso_639_3_entry')
        for elm in it:
            lang = elm.attrib["name"]
            code = elm.attrib["id"]
            if not code in self._lang:
                self._lang[code] = lang
        
        # read countries
        et = ElementTree(file="/usr/share/xml/iso-codes/iso_3166.xml")
        it = et.getiterator('iso_3166_entry')
        for elm in it:
            if "common_name" in elm.attrib:
                descr = elm.attrib["common_name"]
            else:
                descr = elm.attrib["name"]
            if "alpha_2_code" in elm.attrib:
                code = elm.attrib["alpha_2_code"]
            else:
                code = elm.attrib["alpha_3_code"]
            self._country[code] = descr
            
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
        if code in self._lang:
            return self._lang[code]
        return ""

    def country(self, code):
        """ map country code to country name"""
        if code in self._country:
            return self._country[code]
        return ""

    def generated_locales(self):
        """ return a list of locales available on the system
            (running locale -a) """
        locales = []
        p = subprocess.Popen(["locale", "-a"], stdout=subprocess.PIPE)
        for line in string.split(p.communicate()[0], "\n"):
            tmp = line.strip()
            if tmp.startswith("#") or tmp == "" or tmp == "C" or tmp == "POSIX":
                continue
            # we are only interessted in the locale, not the codec
            locale = string.split(tmp)[0]
            locale = string.split(locale,".")[0]
            #locale = string.split(locale,"@")[0]
            if not locale in locales:
                locales.append(locale)
        #print locales
        return locales

    def translate_language(self, lang):
        "return translated language"
        lang_name = gettext.dgettext('iso_639', self._lang[lang])
        if lang_name == self._lang[lang]:
            lang_name = gettext.dgettext('iso_639_3', self._lang[lang])
        return lang_name

    def translate_locale(self, locale):
        """
        return translated language and country of the given
        locale into the given locale, e.g. 
        (Deutsch, Deutschland) for de_DE
        """

        macr = macros.LangpackMacros(locale)

        #(lang, country) = string.split(locale, "_")
        country = macr['CCODE']
        current_language = None
        if "LANGUAGE" in os.environ:
            current_language = os.environ["LANGUAGE"]
        os.environ["LANGUAGE"]=locale
        lang_name = self.translate_language(macr['LCODE'])
        country_name = gettext.dgettext('iso_3166', self._country[country])
        if current_language:
            os.environ["LANGUAGE"] = current_language
        return (lang_name, country_name)

    def translate(self, locale):
        """ get a locale code and output a human readable name """
        macr = macros.LangpackMacros(locale)
        if "_" in locale:
            #(lang, country) = string.split(locale, "_")
            (lang_name, country_name) = self.translate_locale(locale)
            # get all locales for this language
            l = filter(lambda k: k.startswith(macr['LCODE']), self.generated_locales())
            # only show region/country if we have more than one 
            if len(l) > 1:
                mycountry = self.country(macr['CCODE'])
                if mycountry:
                    return "%s (%s)" % (lang_name, country_name)
                else:
                    return lang_name
            else:
                return lang_name
        return self.translate_language(locale)

    def makeEnvString(self, code):
        """ input is a language code, output a string that can be put in
            the LANGUAGE enviroment variable.
            E.g: en_DK -> en_DK:en
        """
        # first check if we got somethign from languagelist
        if code in self._languagelist:
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
    li = LocaleInfo("%s/data/languagelist" % datadir)

    print "default: '%s'" % li.getDefaultLanguage()

    print li._lang
    print li._country
    print li._languagelist
    print li.generated_locales()
