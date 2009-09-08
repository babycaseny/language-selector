'''macros.py: Generate macro values from configuration values and provide
substitution functions.

The following macros are available:

  LCODE CCODE PKGCODE
'''

import re, os.path, os

def _file_map(file, key, sep = None):
    '''Look up key in given file ("key value" lines). Throw an exception if
    key was not found.'''

    val = None
    for l in open(file):
        try:
            (k, v) = l.split(sep)
        except ValueError:
            continue
        # sort out comments
        if k.find('#') >= 0 or v.find('#') >= 0:
            continue
        if k == key:
            val = v.strip()
    if val == None:
        raise KeyError, 'Key %s not found in %s' % (key, file)
    return val

class LangcodeMacros:
    
    LANGCODE_TO_LOCALE = '/usr/share/language-selector/data/langcode2locale'

    def __init__(self, langCode):
        self.macros = {}
        locales = {}
        for l in open(self.LANGCODE_TO_LOCALE):
            try:
                l = l.rstrip()
                (k, v) = l.split(':')
            except ValueError:
                continue
            if k.find('#') >= 0 or v.find('#') >= 0:
                continue
            if not locales.has_key(k):
                locales[k] = []
            locales[k].append(v)
        self['LOCALES'] = locales[langCode]

    def __getitem__(self, item):
        # return empty string as default
        return self.macros.get(item, '')

    def __setitem__(self, item, value):
        self.macros[item] = value

    def __contains__(self, item):
        return self.macros.__contains__(item)

class LangpackMacros:

    LOCALE_TO_LANGPACK = '/usr/share/language-selector/data/locale2langpack'    

    def __init__(self, locale):
        '''Initialize values of macros.

        This uses information from maps/, config/, some hardcoded aggregate
        strings (such as package names), and some external input:
        
        - locale: Standard locale representation (e. g. pt_BR.UTF-8)
        '''
        self.macros = {}
        # chop .* and @* suffixes to get encoding-agnostic locale
        self['LOCALE'] = (locale.split('.')[0])
        try:
            (self['LLCC'], self['VARIANT']) = self['LOCALE'].split('@')
        except ValueError:
            self['LLCC'] = self['LOCALE']
            self['VARIANT'] = ''

        # language and country
        try:
            (self['LCODE'], self['CCODE']) = self['LLCC'].split('_')
        except ValueError:
            self['LCODE'] = self['LLCC']

        if not self['LCODE']:
            raise Exception, 'Internal error: LCODE is empty'

        # package code
        try:
            self['PKGCODE'] = _file_map(self.LOCALE_TO_LANGPACK, '%s-%s' % (self['LCODE'], self['CCODE'].lower()), ':')
        except KeyError:
            self['PKGCODE'] = self['LCODE']

    def __getitem__(self, item):
        # return empty string as default
        return self.macros.get(item, '')

    def __setitem__(self, item, value):
        self.macros[item] = value

    def __contains__(self, item):
        return self.macros.__contains__(item)

    def subst_string(self, s):
        '''Substitute all macros in given string.'''

        re_macro = re.compile('%([A-Z]+)%')
        while 1:
            m = re_macro.search(s)
            if m:
                s = s[:m.start(1)-1] + self[m.group(1)] + s[m.end(1)+1:]
            else:
                break

        return s

    def subst_file(self, file):
        '''Substitute all macros in given file.'''

        s = open(file).read()
        open(file, 'w').write(self.subst_string(s))

    def subst_tree(self, root):
        '''Substitute all macros in given directory tree.'''

        for path, dirs, files in os.walk(root):
            for f in files:
                self.subst_file(os.path.join(root, path, f))

if __name__ == '__main__':
    for locale in ['de', 'de_DE', 'de_DE.UTF-8', 'de_DE.UTF-8@euro', 'fr_BE@latin', 'zh_CN.UTF-8', 'zh_TW.UTF-8', 'zh_HK.UTF-8']:
        l = LangpackMacros(locale)
        print '-------', locale, '---------------'
        template = '"%PKGCODE%: %LCODE% %CCODE% %VARIANT%"'
        print 'string:', l.subst_string(template)

        open('testtest', 'w').write(template)
        l.subst_file('testtest')
        print 'file  :', open('testtest').read()
        os.unlink('testtest')

