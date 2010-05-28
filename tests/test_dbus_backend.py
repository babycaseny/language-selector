#!/usr/bin/python

import apt
import apt_pkg
import glib
import unittest

import sys
sys.path.insert(0, "../")

from dbus_backend.lsd import *

import dbus.mainloop.glib 
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True) 

class TestDbusBackend(unittest.TestCase):

    def setUp(self):
        apt_pkg.Config.Set("Dir::State::lists","./test-data/var/lib/apt/lists.cl")
        apt_pkg.Config.Set("Dir::State::status","./test-data/var/lib/dpkg/status")
        apt_pkg.Config.Set("Dir::Etc::SourceList","./test-data/etc/apt/sources.list.cl")
        apt_pkg.Config.Set("Dir::Etc::SourceParts","x")
        logging.info("updating the cache")
        self.cache = apt.Cache()
        self.cache.update()
        # create private bus
        self.bus = dbus.bus.BusConnection()
        # put langauge-selector-server on it
        self.lss = LanguageSelectorServer(bus=self.bus, datadir="..")

    def test_dbus_server(self):
        pkgs = self.lss.GetMissingPackages("de", None, None)
        self.assertTrue("openoffice.org-help-de" in pkgs)

    def test_dbus_server_async(self):
        def _signal(pkgs):
            self.pkgs = pkgs
        self.pkgs = None
        # monkey patch signal handler
        # FIXME: use proxy object and connect_to_signal() instead
        self.lss.MissingLanguagePackages = _signal
        self.lss.GetMissingPackagesAsync("de", None, None)
        main_loop = glib.main_context_default()
        while not self.pkgs:
            main_loop.iteration()
        self.assertTrue("openoffice.org-help-de" in self.pkgs)

if __name__ == "__main__":
    apt_pkg.Config.Set("Apt::Architecture","i386")
    unittest.main()
