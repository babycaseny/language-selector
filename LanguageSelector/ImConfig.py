# ImConfig.py (c) 2012 Canonical
# Author: Gunnar Hjalmarsson <gunnarhj@ubuntu.com>
#
# Released under the GPL
#

import os
import subprocess

class ImConfig(object):
    
    def __init__(self):
        pass

    def available(self):
        return os.path.exists('/usr/bin/im-config')

    def getAvailableInputMethods(self):
        inputMethods = subprocess.check_output(['im-config', '-l']).decode().split()
        return ['default'] + sorted(inputMethods)

    def getCurrentInputMethod(self):
        user_conf_file = os.path.expanduser('~/.xinputrc')
        if os.path.exists(user_conf_file):
            for line in open(user_conf_file):
                if line.startswith('run_im'):
                    return line.split()[1]
        return 'default'

    def setInputMethod(self, im):
        arg = 'REMOVE' if im == 'default' else im
        subprocess.call(['im-config', '-n', arg])
    
if __name__ == '__main__':
    im = ImConfig()
    print('available input methods: %s' % im.getAvailableInputMethods())
    print("setting method 'fcitx'")
    im.setInputMethod('fcitx')
    print('current method: %s' % im.getCurrentInputMethod())
    print("setting method 'default' (i.e. removing ~/.xinputrc)")
    im.setInputMethod('default')
    print('current method: %s' % im.getCurrentInputMethod())
