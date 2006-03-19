# FontConfig.py (c) 2006 Canonical, released under the GPL
#
# This file implements the fontconfig hack
# 
# The problem is that different languages have different needs for
# fontconfig preferences. While it would be really good to have a single
# config file it seems to be not feasible right now for practial purposes
# (see https://wiki.ubuntu.com/DapperL10nSprint for more information)
#
# so this file implements a hack to add prefered languages based on the
# configuration we got from the CJK community

import glob
import os.path

from LocaleInfo import LocaleInfo

class ExceptionNotSymlink(Exception):
    pass
class ExceptionUnconfigured(Exception):
    pass
class ExceptionNoConfigForLocale(Exception):
    pass

class FontConfigHack(object):
    """ abstract the fontconfig hack """
    def __init__(self,
                 datadir="/usr/share/language-selector/",
                 globalConfDir="/etc/fonts/"):
        self.datadir="%s/fontconfig" % datadir
        self.globalConfDir=globalConfDir
        self.configFile = "%s/language-selector.conf" % self.globalConfDir
        self.li = LocaleInfo("%s/data/languages" % datadir,
                             "%s/data/countries" % datadir,
                             "%s/data/languagelist" % datadir)
    def getAvailableConfigs(self):
        """ get the configurations we have as a list of languages
            (returns a list of ['zh_CN','zh_TW'])
        """
        res = []
        for name in glob.glob("%s/*" % self.datadir):
            res.append(os.path.basename(name))
        return res
    def getCurrentConfig(self):
        """ returns the current language configuration as a string (e.g. zh_CN)
        
            if the configfile is not a symlink it raises a
             ExceptionNotSymlink exception
            if the file dosn't exists raise a
             ExceptionUnconfigured exception
            if it's unconfigured return the string 'none'
        """
        f = self.configFile
        if not os.path.exists(f):
            raise ExceptionUnconfigured()
        if not os.path.islink(f):
            raise ExceptionNotSymlink()
        realpath = os.path.realpath(f)
        return os.path.basename(realpath)

    def setConfig(self, locale):
        """ set the configuration for 'locale'. if locale can't be
            found a NoConfigurationForLocale exception it thrown
        """
        # check if we have a config
        if locale not in self.getAvailableConfigs():
            raise ExceptionNoConfigForLocale()
        # do sanity checking (is it really a symlink?)
        if os.path.exists(self.configFile) and not os.path.islink(self.configFile):
            raise ExceptionNotSymlink()
        # remove existing symlink
        if os.path.exists(self.configFile):
            os.unlink(self.configFile)
        # do the actual symlink
        os.symlink(os.path.normpath("%s/%s"% (self.datadir, locale)),
                   self.configFile)
        
    def setConfigBasedOnLocale(self):
        """ set the configuration based on the locale in LocaleInfo. If
            no configuration is found the fontconfig config is set to
            'none'
            Can throw a exception
        """
        lang = self.li.getDefaultLanguage()
        self.setConfig(lang)
        

if __name__ == "__main__":
    datadir = "/usr/share/language-selector/data"

    li = LocaleInfo("%s/languages" % datadir,
                    "%s/countries" % datadir,
                    "%s/languagelist" % datadir)

    fc = FontConfigHack()

    # clean up
    os.unlink(fc.configFile)
    
    print fc.getAvailableConfigs()
    try:
        config = fc.getCurrentConfig()
    except ExceptionNotSymlink:
        print "not symlink"
    except ExceptionUnconfigured:
        print "unconfigured"

    print fc.setConfigBasedOnLocale()
    print fc.getCurrentConfig()
