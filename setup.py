#!/usr/bin/env python

from distutils.core import setup
import glob
import os
import sys

GETTEXT_NAME="language-selector"
I18NFILES = []
for filepath in glob.glob("po/mo/*/LC_MESSAGES/*.mo"):
    lang = filepath[len("po/mo/"):]
    targetpath = os.path.dirname(os.path.join("share/locale",lang))
    I18NFILES.append((targetpath, [filepath]))

# HACK: make sure that the mo files are generated and up-to-date
if sys.argv[1] == "build":
    assert(os.system("cd data; make") == 0)
    assert(os.system("cd LanguageSelector/qt; make") == 0)
    assert(os.system("make -C po") == 0)
    assert(os.system("cd dbus_backend; make") == 0)
    
setup(name='language-selector',
      version='0.1',
      packages=['LanguageSelector',
                'LanguageSelector.gtk',
                'LanguageSelector.qt'],
      scripts=['qt-language-selector',
               'gnome-language-selector',
               'check-language-support',
               'fontconfig-voodoo'],
      data_files=[('share/language-selector/data',
                   ["data/language-selector.png",
                    "data/languagelist",
                    "data/langcode2locale",
                    "data/locale2langpack",
                    "data/pkg_depends",
                    "data/variants",
                    "data/blacklist",
                    "data/im-switch.blacklist",
                    "data/LanguageSelector.ui"]),
                  ('share/applications',
                   glob.glob("data/*.desktop")),
                  # dbus stuff
                  ('share/dbus-1/system-services',
                   ['dbus_backend/com.ubuntu.LanguageSelector.service']),
                  ('../etc/dbus-1/system.d/',
                   ["dbus_backend/com.ubuntu.LanguageSelector.conf"]),
                  ('lib/language-selector/',
                   ["dbus_backend/ls-dbus-backend"]),
                  ('share/polkit-1/actions/',
                   ["dbus_backend/com.ubuntu.languageselector.policy"]),
                  # pretty pictures
                  ('share/pixmaps',
                   ["data/language-selector.png"]),
                  ]+I18NFILES,
      )


