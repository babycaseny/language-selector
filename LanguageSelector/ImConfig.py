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
        # FIXME: This function is a little hackish. It should be
        # possible to make use of im-config code instead.
        inputMethods = []
        packages_to_check = ['ibus', 'fcitx', 'uim', 'hime', 'gcin',
                             'scim', 'nabi', 'gtk3-im-libthai']
        packinfo = subprocess.Popen(['dpkg-query', '-l'] +
          packages_to_check, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
          universal_newlines=True).communicate()[0]
        for pack in packages_to_check:
            if 'ii  %s' % pack in packinfo:
                if pack == 'nabi':
                    inputMethods.append('hangul')
                elif pack == 'gtk3-im-libthai':
                    inputMethods.append('thai')
                else:
                    inputMethods.append(pack)
        return ['default'] + sorted(inputMethods) + ['none']

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
