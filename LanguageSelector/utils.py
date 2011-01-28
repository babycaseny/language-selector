# (c) 2006 Canonical
# Author: Michael Vogt <michael.vogt@ubuntu.com>
#
# Released under the GPL
#

import os
import re
import string
import tempfile

import macros
from LocaleInfo import LocaleInfo

def find_string_and_replace(findString, setString, file_list, 
                            startswith=True, append=True):
    """ find all strings that startswith findString and replace them with
        setString
    """
    for fname in file_list:
        out = tempfile.NamedTemporaryFile(delete=False,
                                          dir=os.path.dirname(fname))
        foundString = False
        if (os.path.exists(fname) and
            os.access(fname, os.R_OK)):
            # look for the line
            for line in open(fname):
                tmp = string.strip(line)
                if startswith and tmp.startswith(findString):
                    foundString = True
                    line = setString
                if not startswith and tmp == findString:
                    foundString = True
                    line = setString
                out.write(line)
        # if we have not found them append them
        if not foundString and append:
            out.write(setString)
        out.flush()
        # rename is atomic
        os.rename(out.name, fname)
        os.chmod(fname, 0644)

def language2locale(language, datadir):
    """ generate locale name for the LC_MESSAGES environment variable
    """
    first_elem = language.split(':')[0]
    macr = macros.LangpackMacros(datadir, first_elem)
    locales = []
    localeinfo = LocaleInfo('languagelist', datadir)
    for locale in localeinfo.generated_locales():
        if re.split('[_@]', locale)[0] == macr['LCODE']:
            locales.append(locale)        
    # exact match
    if macr['LOCALE'] in locales:
        return macr['SYSLOCALE']
    if not macr['CCODE']:
        # try the "main" country code if any
        f = open(os.path.join(datadir, 'data', 'main-countries'), 'r')
        for line in f.readlines():
            if line.startswith('#') or not line.strip(): continue
            (lcode, ll_CC) = line.split()
            if lcode == macr['LCODE']:
                try_me = first_elem.replace(lcode, ll_CC, 1)
                macr = macros.LangpackMacros(datadir, try_me)
                if macr['LOCALE'] in locales:
                    return macr['SYSLOCALE']
                break
        # try out fitting locale with any country code
        for locale in locales:
            m = re.match('(([a-z]+)_[A-Z]+)', locale)
            if m:
                ll_CC, lcode = m.groups()
                try_me = first_elem.replace(lcode, ll_CC, 1)
                macr = macros.LangpackMacros(datadir, try_me)
                if macr['LOCALE'] in locales:
                    return macr['SYSLOCALE']
    # failed
    return ''

