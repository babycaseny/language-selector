# ImSwitch.py (c) 2006 Canonical, released under the GPL
#
# This file implements a interface to im-switch
#

from LocaleInfo import LocaleInfo
import os.path
import sys

class ImSwitch(object):
    confdir = "/etc/X11/xinit/xinput.d/"
    
    def __init__(self):
        pass
    def getAvailableInputMethods(self):
        """ get the input methods available via im-switch """
        inputMethods = []
        for dentry in os.listdir(self.confdir):
            if not os.path.islink(self.confdir+dentry):
                inputMethods.append(dentry)
        inputMethods.sort()
        return inputMethods

    def setDefaultInputMethod(self, method, locale="all_ALL"):
        """ sets the default input method for the given locale
            (in ll_CC form)
        """
        l = self.confdir+locale
        if os.path.islink(l):
            os.unlink(l)
        os.symlink(self.confdir+method, l)
        return True

    def resetDefaultInputMethod(self, locale="all_ALL"):
        """ reset the default input method to auto (controlled by
            im-switch
        """
        d = "/etc/alternatives/xinput-%s" % locale
        l = self.confdir+locale
        if os.path.islink(l):
            os.unlink(l)
        os.symlink(d, self.confdir+locale)
        return True
        
    def getCurrentInputMethod(self, locale="all_ALL"):
        """ get the current default input method for the selected
            locale (in ll_CC form)
        """
        return os.path.basename(os.path.realpath(self.confdir+locale))
        
if __name__ == "__main__":
    im = ImSwitch()
    print "available input methods: "
    print im.getAvailableInputMethods()
    print "current method: ",
    print im.getCurrentInputMethod()
    print "switching to 'th-xim': ",
    print im.setDefaultInputMethod("th-xim")
    print "current method: ",
    print im.getCurrentInputMethod()
    print "reset default: ",
    print im.resetDefaultInputMethod()
    print "current method: ",
    print im.getCurrentInputMethod()
