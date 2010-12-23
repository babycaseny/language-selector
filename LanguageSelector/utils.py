# (c) 2006 Canonical
# Author: Michael Vogt <michael.vogt@ubuntu.com>
#
# Released under the GPL
#

import os
import string
import tempfile
import subprocess
import re

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

def language2locale(language):
    firstLanguage = language.split(':')[0]
    locales = []
    locale = ''
    p = subprocess.Popen(['locale', '-a'], stdout=subprocess.PIPE)
    for loc in p.communicate()[0].split("\n"):
        if loc.find('.utf8') > 0:
            locales.append(loc)
    for loc in locales:
        if firstLanguage == loc.replace('.utf8', ''):
            locale = loc
            break
    if not locale:
        for loc in locales:
            if re.split('[_@]', firstLanguage)[0] == re.split('[._@]', loc)[0]:
                locale = loc
                break
    if not locale:
        locale = 'en_GB.utf8'
    return locale

