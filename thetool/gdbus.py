'''
Created on Nov 9, 2012

@author: ivan
'''

from array import array
import logging
log=logging.getLogger("gdbus")
from gi.repository import Gio, GLib, GObject
from collections import defaultdict
from copy import copy
import utils


BUS_TYPES={'session':Gio.BusType.SESSION, 'system': Gio.BusType.SYSTEM}
class DBusProxyWrapper(object): 
    def __init__(self, bus_type, bus_name, object_path, interface, sync_props=False, receive_signals=False):
        self.bus_type=bus_type
        self.bus_name=bus_name
        self.interface=interface
        self.object_path=object_path
        self.sync_props=sync_props
        self.receive_signals=receive_signals
        
        bus_type=BUS_TYPES.get(bus_type)
        if not bus_type:
            raise ValueError('Invalid bus type')
        flags=Gio.DBusProxyFlags.DO_NOT_AUTO_START
        if not receive_signals:
            flags|=Gio.DBusProxyFlags.DO_NOT_CONNECT_SIGNALS
        self._proxy=Gio.DBusProxy.new_for_bus_sync(bus_type, 
                        flags, None,
                        bus_name, object_path,interface, None)
        
        if not self._proxy:
            raise RuntimeError('Cannot load proxy for %s' % interface)
        if receive_signals:
            self._proxy_sig=self._proxy.connect('g-signal', self._receive_signal)
        self._props_proxy=None
        try:
            self._props_proxy=Gio.DBusProxy.new_for_bus_sync(bus_type, 
                    flags, None, bus_name, object_path,
                    'org.freedesktop.DBus.Properties', None)
            if not self._props_proxy:
                log.warn('Cannot init properties interface for object - %s', object_path)
            else:
                # Will catch also properties changed on Properties interface
                if receive_signals:
                    self._props_proxy_sig=self._props_proxy.connect('g-signal', self._receive_signal)
        except Exception,e:
            log.warn('Cannot init properties interface for object - %s, error %s', object_path,e)
            
        self._listeners=defaultdict(lambda: set())   
    
    def fake_signal(self, sender_name, signal, params):  
        self._receive_signal('g-signal', sender_name, signal, params) 
         
    def disconnect(self):    
        if self.receive_signals:
            hasattr(self,'_proxy_sig') and self._proxy.disconnect(self._proxy_sig)
            hasattr(self, 'props_proxy_sig') and self._props_proxy.disconnect(self._props_proxy_sig)
    def add_listener(self,signal, call_back):
        self._listeners[signal].add(call_back)
        
    def remove_listener(self,signal, call_back):
        try:
            self._listeners[signal].remove(call_back)
        except Exception, e:
            log.warn("cannot remove listener %s from %s - %s", call_back, signal,e)
            
    def _receive_signal(self, proxy, sender_name, signal, params, user_data=None):
        params=params.unpack() if hasattr(params, 'unpack') else params
        log.debug('Received signal %s on object %s sender %s params %s',  signal, self.object_path, sender_name, params)
        listeners=copy(self._listeners[signal])
        for l in listeners:
            #todo - should call with idle? or thread save
            l(*params)
            
    def __getattr__(self, name):
        #TODO - this method is not working very well because some objects to not get cached 
        # properties - like org.mpris.MediaPlayer2.vlan -  why???
        names=self._proxy.get_cached_property_names()
        if name in names:
            return self.get_property(name)
        else:
            return getattr(self._proxy,name)
        
    def get_property(self, name):
        if self.sync_props and hasattr(self, '_props_proxy') and self._props_proxy:
            #log.debug('Getting property %s from remote object %s', name, self.object_path)
            val= self._props_proxy.call_sync('Get', GLib.Variant('(ss)',(self.interface, name)),
                Gio.DBusCallFlags.NONE, -1, None)
            self._proxy.set_cached_property(name, val)
            
        else:
            val=self._proxy.get_cached_property(name)
        if val:
            return self._unpack_value(val)
        
    def _unpack_value(self, val):
        result=val.unpack()
        # to be compatible with standard Python behaviour, unbox
        # single-element tuples and return None for empty result tuples
        if len(val) == 1:
            result = result[0]
        elif len(result) == 0:
            result = None
        return result
        
    def to_object(self, path, interface=None, klass=None, **kwargs):
        if not interface and not klass:
            raise ValueError('Must specify either interface of klass')
        if klass:
            if not issubclass(klass, DBusProxyWrapper):
                raise ValueError('klass mus be subclass of DBusProxyWrapper')
            return klass(path, **kwargs)
        else:
            return DBusProxyWrapper(self.bus_type, self.bus_name, path, interface, sync_props=self.sync_props)
    def get_object_path(self):
        return self.object_path

def list_names(bus_type):
    bus_type=BUS_TYPES.get(bus_type)
    if not bus_type:
        raise ValueError('Invalid bus type')
    flags=Gio.DBusProxyFlags.DO_NOT_AUTO_START
    proxy=Gio.DBusProxy.new_for_bus_sync(bus_type, 
                        flags, None,
                        'org.freedesktop.DBus', '/org/freedesktop/DBus',
                        'org.freedesktop.DBus', None)
    names=proxy.ListNames()
    return names
        
class UPower(DBusProxyWrapper):
    def __init__(self):
        super(UPower, self).__init__("system", 'org.freedesktop.UPower', 
                '/org/freedesktop/UPower', 'org.freedesktop.UPower')
        
class ConsoleKit(DBusProxyWrapper):
    def __init__(self):
        super(ConsoleKit, self).__init__("system", 'org.freedesktop.ConsoleKit', 
                '/org/freedesktop/ConsoleKit/Manager', 'org.freedesktop.ConsoleKit.Manager')   


def power_off(power_off_type):
    if power_off_type=='shutdown':
        ConsoleKit().Stop()
    elif power_off_type=='suspend':
        UPower().Suspend()
    elif power_off_type=='hibernate':
        UPower().Hibernate()
        
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