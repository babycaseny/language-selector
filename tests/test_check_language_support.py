#!/usr/bin/python

import apt
import apt_pkg
import logging
import sys
import unittest

sys.path.insert(0, "../")

from LanguageSelector.CheckLanguageSupport import *

class TestCheckLanguageSupport(unittest.TestCase):

    def setUp(self):
        apt_pkg.Config.set("Dir::State::lists","./test-data/var/lib/apt/lists.cl")
        apt_pkg.Config.set("Dir::State::status","./test-data/var/lib/dpkg/status")
        apt_pkg.Config.set("Dir::Etc::SourceList","./test-data/etc/apt/sources.list.cl")
        apt_pkg.Config.set("Dir::Etc::SourceParts","x")
        logging.info("updating the cache")
        self.cache = apt.Cache()
        self.cache.update()
        self.cache.open()

    def assure_in_missing(self, pkgname, missing):
        logging.debug("looking for '%s' in '%s'" % (pkgname, missing))
        self.assertTrue(pkgname in missing,
                        "expected '%s' in '%s'" % (pkgname, missing))

    def test_check_language_support(self):
        """ if we get what we expect """
        cl = CheckLanguageSupport("..", self.cache)

        missing = cl.getMissingPackages("ar", True, None)
        self.assure_in_missing("libreoffice-l10n-ar", missing)
        # 5 is picked at random, just need to ensure that the list 
        # contains a bunch of entries
        self.assertTrue(len(missing) > 5, "missing list very small")

        missing = cl.getMissingPackages("ar", True, ["libreoffice-common"])
        self.assure_in_missing("libreoffice-l10n-ar", missing)

        missing = cl.getMissingPackages("fi", True, ["firefox"])
        self.assure_in_missing("mozvoikko", missing)
        
        missing = cl.getMissingPackages("fi", True, ["firefox", "thunderbird"])
        self.assure_in_missing("mozvoikko", missing)
        self.assure_in_missing("thunderbird-locale-fi", missing)

        #self.assert_(ls.verifyPackageLists() == False,
        #              "verifyPackageLists returned True for a empty list")
        


if __name__ == "__main__":
    #logging.basicConfig(level=logging.DEBUG)
    apt_pkg.Config.set("Apt::Architecture","i386")
    unittest.main()
