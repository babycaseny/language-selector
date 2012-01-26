#!/usr/bin/python

import apt
import subprocess

DEFAULT_DEPENDS_FILE='/usr/share/language-selector/data/pkg_depends'

class LanguageSupport:
    lang_country_map = None

    def __init__(self, apt_cache=None, depends_file=None):
        if apt_cache is None:
            self.apt_cache = apt.Cache()
        else:
            self.apt_cache = apt_cache

        self.pkg_depends = self._parse_pkg_depends(depends_file or
                DEFAULT_DEPENDS_FILE)

    def by_package_and_locale(self, package, locale, installed=False):
        '''Get language support packages for a package and locale.

        Note that this does not include support packages which are not specific
        to a particular trigger package, e. g. general language packs. To get
        those, call this with package==''.

        By default, only return packages which are not installed. If installed
        is True, return all packages instead.
        '''
        packages = []
        depmap = self.pkg_depends.get(package, {})

        # check explicit entries for that locale
        for pkglist in depmap.get(self._langcode_from_locale(locale), {}).values():
            for p in pkglist:
                if p in self.apt_cache:
                    packages.append(p)

        # check patterns for empty locale string (i. e. applies to any locale)
        for pattern_list in depmap.get('', {}).values():
            for pattern in pattern_list:
                for pkg_candidate in self._expand_pkg_pattern(pattern, locale):
                    if pkg_candidate in self.apt_cache:
                        packages.append(pkg_candidate)

        if not installed:
            # filter out installed packages
            packages = [p for p in packages if not self.apt_cache[p].installed]
        return packages

    def by_locale(self, locale, installed=False):
        '''Get language support packages for a locale.

        Return all packages which need to be installed in order to provide
        language support for the given locale for all already installed
        packages. This should be called after adding a new locale to the
        system.

        By default, only return packages which are not installed. If installed
        is True, return all packages instead.
        '''
        packages = []

        for trigger in self.pkg_depends:
            try:
                if trigger == '' or self.apt_cache[trigger].installed:
                    packages += self.by_package_and_locale(trigger, locale, installed)
            except KeyError:
                continue

        return packages

    def by_package(self, package, installed=False):
        '''Get language support packages for a package.

        This will install language support for that package for all available
        system languages. This is a wrapper around available_languages() and
        by_package_and_locale().

        Note that this does not include support packages which are not specific
        to a particular trigger package, e. g. general language packs. To get
        those, call this with package==''.

        By default, only return packages which are not installed. If installed
        is True, return all packages instead.
        '''
        packages = set()
        for lang in self.available_languages():
            packages.update(self.by_package_and_locale(package, lang, installed))
        return packages

    def missing(self, installed=False):
        '''Get language support packages for current system.

        Return all packages which need to be installed in order to provide
        language support all system locales for all already installed
        packages. This should be called after installing the system without
        language support packages (perhaps because there was no network
        available to download them).

        This is a wrapper around available_languages() and by_locale().

        By default, only return packages which are not installed. If installed
        is True, return all packages instead.
        '''
        packages = set()
        for lang in self.available_languages():
                packages.update(self.by_locale(lang, installed))
        return packages

    def available_languages(self):
        '''List available languages in the system.

        This calls "locale -a" and filters the result for language codes, so
        that iterating over it is a lot smaller than iterating over the full
        locale list. As some languages like English, Portugese, or Chinese have
        meaningful territory codes, these are kept.

        The list items can be passed as the "locale" argument of by_locale(),
        by_package_and_locale(), etc.
        '''
        languages = set()
        locales = subprocess.check_output(['locale', '-a']).decode()
        for locale in locales.splitlines():
            locale = locale.split('.')[0]
            if '_' not in locale:
                continue

            lang = locale.split('_')[0]

            # languages where territory is deciding
            if lang == 'zh':
                languages.add(locale)
                continue

            # languages where territory is relevant; keep the general language,
            # too
            languages.add(lang)
            if locale in ['en_AU', 'en_GB', 'en_US'] or lang in ['es', 'pt',
                    'zh']:
                languages.add(locale)

        return languages

    def _parse_pkg_depends(self, filename):
        '''Parse pkg_depends file.

        Return trigger_package -> langcode -> category -> [dependency,...] map.
        '''
        map = {}
        with open(filename) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                (cat, lc, trigger, dep) = line.split(':')
                map.setdefault(trigger, {}).setdefault(lc, {}).setdefault(cat,
                        []).append(dep)

        return map

    @classmethod
    def _langcode_from_locale(klass, locale):
        '''Turn a locale name into a language code as in pkg_depends.'''

        # special-case Chinese locales, as they are split between -hans and
        # -hant
        if locale.startswith('zh_CN') or locale.startswith('zh_SG'):
            return 'zh-hans'
        # Hong Kong and Taiwan use traditional
        if locale.startswith('zh_'):
            return 'zh-hant'

        return locale.split('_', 1)[0]

    @classmethod
    def _expand_pkg_pattern(klass, pattern, locale):
        '''Return all possible suffixes for given pattern and locale'''

        locale = locale.split('.', 1)[0].lower()
        variant = None
        country = None
        try:
            (lang, country) = locale.split('_', 1)
            if '@' in country:
                (country, variant) = country.split('@', 1)
        except ValueError:
            lang = locale

        pkgs = ['%s%s' % (pattern, lang)]

        if country:
            pkgs.append('%s%s%s' % (pattern, lang, country))
            pkgs.append('%s%s-%s' % (pattern, lang, country))
        else:
            for country in klass._countries_for_lang(lang):
                pkgs.append('%s%s%s' % (pattern, lang, country))
                pkgs.append('%s%s-%s' % (pattern, lang, country))

        if variant:
            pkgs.append('%s%s-%s-%s' % (pattern, lang, variant))

        if country and variant:
            pkgs.append('%s%s-%s-%s' % (pattern, lang, country, variant))

        # special-case Chinese
        if lang == 'zh':
            if country in ['cn', 'sg']:
                pkgs.append(pattern + 'zh-hans')
            else:
                pkgs.append(pattern + 'zh-hant')

        return pkgs

    @classmethod
    def _countries_for_lang(klass, lang):
        '''Return a list of countries for given language'''

        if klass.lang_country_map is None:
            klass.lang_country_map = {}
            # fill cache
            with open('/usr/share/i18n/SUPPORTED') as f:
                for line in f:
                    line = line.split('#', 1)[0].split(' ')[0]
                    if not line:
                        continue
                    line = line.split('.', 1)[0].split('@')[0]
                    try:
                        (l, c) = line.split('_')
                    except ValueError:
                        continue
                    c = c.lower()
                    klass.lang_country_map.setdefault(l, set()).add(c)

        return klass.lang_country_map.get(lang, [])

def apt_cache_add_language_packs(resolver, cache, depends_file=None):
    '''Add language support for packages marked for installation.
    
    For all packages which are marked for installation in the given apt.Cache()
    object, mark the corresponding language packs and support packages for
    installation as well.

    This function can be used as an aptdaemon modify_cache_after plugin.
    '''
    ls = LanguageSupport(cache, depends_file)
    support_pkgs = set()
    for pkg in cache.get_changes():
        if pkg.marked_install:
            support_pkgs.update(ls.by_package(pkg.name))

    for pkg in support_pkgs:
        cache[pkg].mark_install(from_user=False)

