'''
Created on Nov 9, 2012

@author: ivan
'''

import os
import sys
import traceback
import logging
log=logging.getLogger("gdbus")
from gi.repository import Gio, GLib, GObject
from collections import defaultdict

class DBusProxyWrapper(object): 
    BUS_TYPES={'session':Gio.BusType.SESSION, 'system': Gio.BusType.SYSTEM}
    
    def __init__(self, bus_type, bus_name, object_path, interface, sync_props=False):
        self.bus_name=bus_name
        self.interface=interface
        self.opject_path=object_path
        self.sync_props=sync_props
        bus_type=self.BUS_TYPES.get(bus_type)
        if not bus_type:
            raise ValueError('Invalid bus type')
        
        self._proxy=Gio.DBusProxy.new_for_bus_sync(Gio.BusType.SYSTEM, 
                        Gio.DBusProxyFlags.DO_NOT_AUTO_START, None,
                        bus_name, object_path,interface, None)
        
        if not self._proxy:
            raise RuntimeError('Cannot load proxy for %s' % interface)
        self._proxy.connect('g-signal', self._receive_signal)
        
        try:
            self._props_proxy=Gio.DBusProxy.new_for_bus_sync(Gio.BusType.SYSTEM, 
                    Gio.DBusProxyFlags.DO_NOT_AUTO_START, None,
                        bus_name, object_path,
                    'org.freedesktop.DBus.Properties', None)
        except Exception,e:
            log.warn('Cannot init properties interface for object - %s', object_path,e)
            
        self._listeners=defaultdict(lambda: set())   
        
        
    def add_listener(self,signal, call_back):
        self._listeners[signal].add(call_back)
        
    def remove_listener(self,signal, call_back):
        try:
            self._listeners[signal].remove(call_back)
        except Exception, e:
            log.warn("cannot remove listener %s from %s - %s", call_back, signal,e)
            
    def _receive_signal(self, proxy, sender_name, signal, params, user_data=None):
        params=params.unpack()
        log.debug('Received signal %s on interface %s sender %s',  signal, self.interface, sender_name)
        for l in self._listeners[signal]:
            #todo - should call with idle? or thread save
            l(*params)
            
    def __getattr__(self, name):
        names=self._proxy.get_cached_property_names()
        if name in names:
            if self.sync_props and hasattr(self, '_props_proxy') and self._props_proxy:
                log.debug('Getting property %s from remote object %s', name, self.opject_path)
                val= self._props_proxy.call_sync('Get', GLib.Variant('(ss)',(self.interface, name)),
                    Gio.DBusCallFlags.NONE, -1, None)
                self._proxy.set_cached_property(name, val)
                return val.unpack()
            else:
                return self._proxy.get_cached_property(name).unpack()
        else:
            return getattr(self._proxy,name)
        
class NetworkManager (DBusProxyWrapper):
    def __init__(self):
        super(NetworkManager, self).__init__("system", 'org.freedesktop.NetworkManager', 
                '/org/freedesktop/NetworkManager', 'org.freedesktop.NetworkManager', True)
        def echo(*args):
            log.debug( "NM Prop.Changes args %s", args)
        self.add_listener('PropertiesChanged', echo)
        
class UPower(DBusProxyWrapper):
    def __init__(self):
        super(UPower, self).__init__("system", 'org.freedesktop.UPower', 
                '/org/freedesktop/UPower', 'org.freedesktop.UPower')
        
class ConsoleKit(DBusProxyWrapper):
    def __init__(self):
        super(ConsoleKit, self).__init__("system", 'org.freedesktop.ConsoleKit', 
                '/org/freedesktop/ConsoleKit/Manager', 'org.freedesktop.ConsoleKit.Manager')   

        
def main():
    
    
#    logging.basicConfig(level=logging.DEBUG)
#    nm=NetworkManager()
#    print "version ",nm.Version
#    print nm.GetDevices()
#    GObject.MainLoop().run()
    
    up=UPower()
    print up.SuspendAllowed()

#    ck=ConsoleKit()
#    ck.Stop()
    
 
if __name__ == "__main__":
    main()