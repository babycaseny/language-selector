import apt
import apt_pkg

from gettext import gettext as _

# the language-support information
class LanguageInformation(object):
    def __init__(self):
        self.language = None
        self.languageCode = None
        # langPack stuff
        self.hasLangPack = False
        self.langPackInstalled = False
        self.installLangPack = False
        # langSupport stuff
        self.hasLangSupport = False
        self.langSupportInstalled =False
        self.installLangSupport = False 
    def __str__(self):
        return "%s (%s)" % (self.language, self.languageCode)

# the pkgcache stuff
class ExceptionPkgCacheBroken(Exception):
    pass

class LanguageSelectorPkgCache(apt.Cache):

    # packages that need special translation packs (not covered by
    # the normal langpacks) 
    pkg_translations = [
        ("kdelibs-data", "language-pack-kde-"),
        ("libgnome2-common", "language-pack-gnome-"),
        ("firefox", "mozilla-firefox-locale-"),
        ("mozilla-thunderbird", "mozilla-thunderbird-local-"),
        ("openoffice.org", "openoffice.org-l10n-"),
        ("openoffice.org", "openoffice.org-help-"),
        ("libsword5c2a", "sword-language-pack-")
    ]


    def __init__(self, localeinfo, progress):
        apt.Cache.__init__(self, progress)
        if self._depcache.BrokenCount > 0:
            raise ExceptionPkgCacheBroken()
        self._localeinfo = localeinfo
        # keep the lists 
        self.to_inst = []
        self.to_rm = []

    def clear(self):
        """ clear the selections """
        self._depcache.Init()
        
    def getChangesList(self):
        to_inst = []
        to_rm = []
        for pkg in self.getChanges():
            if pkg.markedInstall or pkg.markedUpgrade:
                to_inst.append(pkg.name)
            if pkg.markedDelete:
                to_rm.append(pkg.name)
        return (to_inst,to_rm)

    def _getPkgList(self, languageCode):
        """ helper that returns the list of needed pkgs for the language """
        # normal langpack+support first
        pkg_list = ["language-support-%s"%languageCode,
                      "language-pack-%s"%languageCode]
        # see what additional pkgs are needed
        for (pkg, translation) in self.pkg_translations:
            if self.has_key(pkg) and self[pkg].isInstalled:
                pkg_list.append(translation+languageCode)
        return pkg_list
        
    def tryInstallLanguage(self, languageCode):
        """ mark the given language for install """
        to_inst = []
        for name in self._getPkgList(languageCode):
            if self.has_key(name):
                try:
                    self[name].markInstall()
                    to_inst.append(name)
                except SystemError:
                    pass

    def tryRemoveLanguage(self, languageCode):
        """ mark the given language for remove """
        to_rm = []
        for name in self._getPkgList(languageCode):
            if self.has_key(name):
                try:
                    # purge
                    self[name].markDelete(True)
                    to_rm.append(name)
                except SystemError:
                    pass
    
    def getLanguageInformation(self):
        """ returns a list with language packs/support packages """
        res = []
        for line in open(self._localeinfo._langFile):
            line = line.strip()
            if line.startswith("#"):
                continue
            (code, lang) = line.split(":")
            li = LanguageInformation()
            li.languageCode = code
            li.language = _(lang)
            li.hasLangPack = self.has_key("language-pack-%s" % code)
            li.hasLangSupport = self.has_key("language-support-%s" % code)
            if li.hasLangPack:
                li.langPackInstalled = li.installLangPack = self["language-pack-%s" % code].isInstalled
            if  li.hasLangSupport:
                li.langSupportInstalled = li.installLangSupport = self["language-support-%s" % code].isInstalled
            if li.hasLangPack or li.hasLangSupport:
                res.append(li)
        return res


if __name__ == "__main__":

    from LocaleInfo import LocaleInfo
    datadir = "/usr/share/language-selector"
    li = LocaleInfo("%s/data/languages" % datadir,
                    "%s/data/countries" % datadir,
                    "%s/data/languagelist" % datadir)

    lc = LanguageSelectorPkgCache(li,apt.progress.OpProgress())
    print "available language information"
    print ", ".join(["%s" %x for x in lc.getLanguageInformation()])

    print "Trying to install 'zh'"
    lc.tryInstallLanguage("zh")
    print lc.getChangesList()

    print "Trying to remove it again"
    lc.tryRemoveLanguage("zh")
    print lc.getChangesList()
