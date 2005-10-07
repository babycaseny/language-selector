# (c) 2005 Canonical
# Author: Michael Vogt <michael.vogt@ubuntu.com>
#
# Released under the GPL
#

import pygtk
pygtk.require('2.0')
import gtk
import gtk.gdk
import gtk.glade
import os.path
import sys

class GladeApp(object):
    " base class for applications build with glade"
    def __init__(self, name="", filename="", datadir=""):
        if name == "":
            self._window_name = "window_%s" % self.__class__.__name__
        else:
            self._window_name = name
        if datadir == "":
            self._datadir = "../data"
        else:
            self._datadir = datadir
        if filename == "":
            filename = "%s/%s.glade" % (self._datadir, self.__class__.__name__)
            if os.path.exists(filename):
                self._glade_file = filename
            else:
                sys.stderr.write("PANIC: can't find glade file: %s\n"%filename)
                sys.exit(1)
        else:
            self._glade_file = filename
        self._glade = gtk.glade.XML(self._glade_file)
        self._win = self._glade.get_widget(self._window_name)
        self._glade.signal_autoconnect(self)

    def run(self):
        self._win.show()
        gtk.main()

class Test(GladeApp):
    def on_button_click_clicked(self, widget):
        print "on_button_click_clicked"

    def on_button_close_clicked(self, widget):
        gtk.main_quit()

if __name__ == "__main__":
    print "Executing self-test"
    a = Test()
    a.run()
    
