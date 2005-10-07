#!/usr/bin/env python

from distutils.core import setup
import glob
import os

GETTEXT_NAME="language-selector"
I18NFILES = []
for filepath in glob.glob("po/mo/*/LC_MESSAGES/*.mo"):
    lang = filepath[len("po/mo/"):]
    targetpath = os.path.dirname(os.path.join("share/locale",lang))
    I18NFILES.append((targetpath, [filepath]))

# HACK: make sure that the mo files are generated and up-to-date
os.system("cd po; make update-po")
    
setup(name='language-selector',
      version='0.1',
      packages=['LanguageSelector'],
      scripts=['gnome-language-selector'],
      data_files=[('share/language-selector/data',
                   ["data/countries",
                    "data/language-selector.png",
                    "data/languagelist",
                    "data/languages",
                    "data/LanguageSelector.glade"]),
                  ('share/applications',
                   ["data/language-selector.desktop"]),
                  ('share/pixmaps',
                   ["data/language-selector.png"])]+I18NFILES,
      )


