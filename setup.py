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
os.system("cd data; make")
os.system("cd LanguageSelector/qt; make")
os.system("cd po; make update-po")
    
setup(name='language-selector',
      version='0.1',
      packages=['LanguageSelector',
                'LanguageSelector.gtk',
                'LanguageSelector.qt'],
      scripts=['qt-language-selector',
               'gnome-language-selector',
               'fontconfig-voodoo'],
      data_files=[('share/language-selector/data',
                   ["data/countries",
                    "data/language-selector.png",
                    "data/languagelist",
                    "data/languages",
                    "data/LanguageSelector.glade"]),
                  ('share/applications',
                   glob.glob("data/*.desktop")),
                  ('share/pixmaps',
                   ["data/language-selector.png"]),
                  ('share/language-selector/fontconfig',
                   glob.glob("fontconfig/*")),
                  ]+I18NFILES,
      )


