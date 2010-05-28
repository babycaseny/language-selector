
import gtk
import dbus
import os

print "pid: ",os.getpid()
session_bus = dbus.SessionBus()
obj = session_bus.get_object('org.freedesktop.PolicyKit.AuthenticationAgent', 
                             '/')
auth = dbus.Interface(obj, "org.freedesktop.PolicyKit.AuthenticationAgent")
res = auth.ObtainAuthorization("com.ubuntu.languageselector.gdmreload",
                               dbus.UInt32(0),
                               dbus.UInt32(os.getpid()))
print "ObtainAuth returned: ", res

system_bus = dbus.SystemBus()
obj = system_bus.get_object('com.ubuntu.LanguageSelector', '/')
iface = dbus.Interface(obj, dbus_interface="com.ubuntu.LanguageSelector")
iface.GdmReload()

res = iface.InstallLanguagePackages(["language-pack-fi"])
print res
