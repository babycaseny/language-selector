
import warnings
warnings.filterwarnings("ignore", "apt API not stable yet", FutureWarning)
import apt
import apt_pkg
import os
import os.path
import macros

from xml.etree.ElementTree import ElementTree

from gettext import gettext as _

class LanguagePackageStatus(object):
    def __init__(self, pkg_template):
        self.pkgname_template = pkg_template
        self.available = False
        self.installed = False
        self.doChange = False


# the language-support information
class LanguageInformation(object):
    def __init__(self):
        #FIXME:
        #needs a new structure:
        #languagePkgList[LANGCODE][tr|fn|in|wa]=[packages available for that language in that category]
        #@property for each category
        #@property for each LANGCODE
        self.language = None
        self.languageCode = None
        # langPack/support status 
        self.languagePkgList = {}
        self.languagePkgList["languagePack"] = LanguagePackageStatus("language-pack-%s")
        self.languagePkgList["languageSupportWritingAids"] = LanguagePackageStatus("language-support-writing-%s")
        self.languagePkgList["languageSupportInputMethods"] = LanguagePackageStatus("language-support-input-%s")
        self.languagePkgList["languageSupportFonts"] = LanguagePackageStatus("language-support-fonts-%s")
        
    @property
    def inconsistent(self):
        " returns True if only parts of the language support packages are installed "
        if (not self.notInstalled and not self.fullInstalled) : return True
        return False
    @property
    def fullInstalled(self):
        " return True if all of the available language support packages are installed "
        for pkg in self.languagePkgList.values() :
            if not pkg.available : continue
            if not ((pkg.installed and not pkg.doChange) or (not pkg.installed and pkg.doChange)) : return False
        return True
    @property
    def notInstalled(self):
        " return True if none of the available language support packages are installed "
        for pkg in self.languagePkgList.values() :
            if not pkg.available : continue
            if not ((not pkg.installed and not pkg.doChange) or (pkg.installed and pkg.doChange)) : return False
        return True
    @property
    def changes(self):
        " returns true if anything in the state of the language packs/support changes "
        for pkg in self.languagePkgList.values() :
            if (pkg.doChange) : return True
        return False
    def __str__(self):
        return "%s (%s)" % (self.language, self.languageCode)

# the pkgcache stuff
class ExceptionPkgCacheBroken(Exception):
    pass

class LanguageSelectorPkgCache(apt.Cache):

    BLACKLIST = "/usr/share/language-selector/data/blacklist"
    LANGCODE_TO_LOCALE = "/usr/share/language-selector/data/langcode2locale"
    PACKAGE_DEPENDS = "/usr/share/language-selector/data/pkg_depends"

    def __init__(self, localeinfo, progress):
        apt.Cache.__init__(self, progress)
        if self._depcache.BrokenCount > 0:
            raise ExceptionPkgCacheBroken()
        self._localeinfo = localeinfo
        # keep the lists 
        self.to_inst = []
        self.to_rm = []

        # packages that need special translation packs (not covered by
        # the normal langpacks)
        self.langpack_locales = {}
        self.pkg_translations = {}
        self.pkg_writing = {}
        filter_list = {}
        blacklist = []
        
        for l in open(self.BLACKLIST):
            l = l.strip()
            if not l.startswith('#'):
                blacklist.append(l)
        
        for l in open(self.LANGCODE_TO_LOCALE):
            try:
                l = l.rstrip()
                if ':' in l:
                    (pkgcode, locale) = l.split(':')
                else:
                    pkgcode = l
                    locale = l
            except ValueError:
                continue
            self.langpack_locales[locale] = pkgcode
        
        for l in open(self.PACKAGE_DEPENDS):
            if l.startswith('#'):
                continue
            try:
                l = l.rstrip()
                # sort out comments
                if l.find('#') >= 0:
                    continue
                (c, lc, k, v) = l.split(':')
            except ValueError:
                continue
            if (c == 'tr' and lc == ''):
                filter_list[v] = k
            elif (c == 'wa' and lc != ''):
                if not lc in self.pkg_writing:
                    self.pkg_writing[lc] = []
                self.pkg_writing[lc].append(("%s" % k, "%s" % v))

        # get list of all packages available on the system and filter them
        for item in self.keys():
            if item in blacklist: 
                continue
            for x in filter_list.keys():
                if item.startswith(x) and not item.endswith('-base'):
                    # parse language code
                    langcode = item.replace(x, '')
                    #print "%s\t%s" % (item, langcode)
                    if langcode == 'zh':
                        # special case: zh langpack split
                        for langcode in ['zh-hans', 'zh-hant']:
                            if not langcode in self.pkg_translations:
                                self.pkg_translations[langcode] = []
                            self.pkg_translations[langcode].append(("%s" % filter_list[x], "%s" % item))
                    elif langcode in self.langpack_locales.values():
                        # langcode == pkgcode
                        if not langcode in self.pkg_translations:
                            self.pkg_translations[langcode] = []
                        self.pkg_translations[langcode].append(("%s" % filter_list[x], "%s" % item))
                        #print self.pkg_translations[langcode]
                    else:
                        # need to scan for LL-CC and LL-VARIANT codes
                        for locale in self.langpack_locales.keys():
                            if '_' in locale or '@' in locale:
                                if '@' in locale:
                                    (locale, variant) = locale.split('@')
                                else:
                                    variant = ''
                                (lcode, ccode) = locale.split('_')
                                if langcode in ["%s-%s" % (lcode, ccode.lower()),
                                                "%s%s" % (lcode, ccode.lower()),
                                                "%s-%s" % (lcode, variant),
                                                "%s%s" % (lcode, variant),
                                                "%s-latn" % lcode,
                                                "%slatn" % lcode,
                                                "%s-%s-%s" % (lcode, ccode.lower(), variant),
                                                "%s%s%s" % (lcode, ccode.lower(), variant)]:
                                    # match found, get matching pkgcode
                                    langcode = self.langpack_locales[locale]
                                    if not langcode in self.pkg_translations:
                                        self.pkg_translations[langcode] = []
                                    self.pkg_translations[langcode].append(("%s" % filter_list[x], "%s" % item))
                                    #print self.pkg_translations[langcode]
                                    break
         
    @property
    def havePackageLists(self):
        " verify that a network package lists exists "
        for metaindex in self._list.List:
            for indexfile in metaindex.IndexFiles:
                if indexfile.ArchiveURI("").startswith("cdrom:"):
                    continue
                if indexfile.ArchiveURI("").startswith("http://security.ubuntu.com"):
                    continue
                if indexfile.Exists and indexfile.HasPackages:
                    return True
        return False

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
        pkg_list = ["language-support-input-%s"%languageCode,\
                    "language-support-writing-%s"%languageCode,\
                    "language-support-fonts-%s"%languageCode,\
                    "language-pack-%s"%languageCode]
        # see what additional pkgs are needed
        #for (pkg, translation) in self.pkg_translations[languageCode]:
        #    if pkg in self and self[pkg].isInstalled:
        #        pkg_list.append(translation)
        return pkg_list
        
    def tryChangeDetails(self, li):
        " change the status of the support details (fonts, input methods) "
        #print li
        for item in li.languagePkgList.values():
            if item.doChange:
                try:
                    if item.installed:
                        self[item.pkgname_template % li.languageCode].markDelete()
                    else:
                        self[item.pkgname_template % li.languageCode].markInstall()
                except SystemError:
                    pass
        # Check for additional translation packages
        item = li.languagePkgList["languagePack"]
        if ((item.installed and not item.doChange) or (item.available and not item.installed and item.doChange)):
            if li.languageCode in self.pkg_translations:
                for (pkg, translation) in self.pkg_translations[li.languageCode]:
                    if pkg in self and \
                       self[pkg].isInstalled and \
                       not self[translation].isInstalled:
                        self[translation].markInstall()
                        #print ("Will pull: %s" % translation)
        elif ((not item.installed and not item.doChange) or (item.installed and item.doChange)) :
            if li.languageCode in self.pkg_translations:
                for (pkg, translation) in self.pkg_translations[li.languageCode]:
                    if pkg in self and \
                       self[pkg].isInstalled and \
                       self[translation].isInstalled:
                           self[translation].markDelete()
                           #print ("Will remove: %s" % translation)

        # Check for additional writing aids packages
        item = li.languagePkgList["languageSupportWritingAids"]
        if ((item.installed and not item.doChange) or (item.available and not item.installed and item.doChange)):
            if li.languageCode in self.pkg_writing:
                for (pkg, pull_pkg) in self.pkg_writing[li.languageCode]:
                    if not pull_pkg in self:
                        continue
                    if '|' in pkg:
                        # multiple dependencies, if one of them is installed, pull the pull_pkg
                        for p in pkg.split('|'):
                            if p in self and \
                               self[p].isInstalled and \
                               not self[pull_pkg].isInstalled:
                                self[pull_pkg].markInstall()
                                #print ("Will pull: %s" % pull_pkg)
                    else:
                        if pkg in self and \
                           self[pkg].isInstalled and \
                           not self[pull_pkg].isInstalled:
                            self[pull_pkg].markInstall()
                            #print ("Will pull: %s" % pull_pkg)
        elif ((not item.installed and not item.doChange) or (item.installed and item.doChange)) :
            if li.languageCode in self.pkg_writing:
                for (pkg, pull_pkg) in self.pkg_writing[li.languageCode]:
                    if not pull_pkg in self:
                        continue
                    if '|' in pkg:
                        # multiple dependencies, if at least one of them is installed, keep the pull_pkg
                        # only remove pull_pkg if none of the dependencies are installed anymore
                        count = 0
                        for p in pkg.split('|'):
                            if p in self and \
                               self[p].isInstalled and \
                               not self[p].markDelete(True) and \
                               not self[p].markInstall(True):
                                count = count+1
                            if count == 0 and self[pull_pkg].isInstalled:
                                self[pull_pkg].markDelete()
                                #print ("Will remove: %s" % pull_pkg)
                    else:
                        if pkg in self and \
                           self[pkg].isInstalled and \
                           self[pull_pkg].isInstalled:
                            self[pull_pkg].markDelete()
                            #print ("Will remove: %s" % pull_pkg)
        return

    def tryInstallLanguage(self, languageCode):
        """ mark the given language for install """
        to_inst = []
        for name in self._getPkgList(languageCode):
            if name in self:
                try:
                    self[name].markInstall()
                    to_inst.append(name)
                except SystemError:
                    pass
                try:
                    self[name].markInstall()
                    to_inst.append(name)
                except SystemError:
                    pass

    def tryRemoveLanguage(self, languageCode):
        """ mark the given language for remove """
        to_rm = []
        for name in self._getPkgList(languageCode):
            if name in self:
                try:
                    # purge
                    self[name].markDelete(True)
                    to_rm.append(name)
                except SystemError:
                    pass
    
    def getLanguageInformation(self):
        """ returns a list with language packs/support packages """
        res = []
        for (code,lang) in self._localeinfo._lang.items():
            if code == 'zh':
                continue
            li = LanguageInformation()
            li.languageCode = code
            li.language = lang
            for langpkg_status in li.languagePkgList.values() :
                pkgname = langpkg_status.pkgname_template % code
                langpkg_status.available = pkgname in self
                if langpkg_status.available:
                    langpkg_status.installed = self[pkgname].isInstalled
            if len(filter(lambda s: s.available, li.languagePkgList.values())) > 0:
                res.append(li)
        return res


if __name__ == "__main__":

    from LocaleInfo import LocaleInfo
    datadir = "/usr/share/language-selector"
    li = LocaleInfo("%s/data/languagelist" % datadir)

    lc = LanguageSelectorPkgCache(li,apt.progress.OpProgress())
    print "available language information"
    print ", ".join(["%s" %x for x in lc.getLanguageInformation()])

    print "Trying to install 'zh'"
    lc.tryInstallLanguage("zh")
    print lc.getChangesList()

    print "Trying to remove it again"
    lc.tryRemoveLanguage("zh")
    print lc.getChangesList()
