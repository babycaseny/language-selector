#!/usr/bin/pyton

from packagekit.client import PackageKitClient
pk = PackageKitClient()
print pk

pkgs = pk.search_name("2vcard")
print pkgs
res = pk.install_packages(pkgs[0])
#res = pk.install_packages('2vcard;0.5-3;all;Ubuntu')
res = pk.remove_packages(pkgs[0])
print res
