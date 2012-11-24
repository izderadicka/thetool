'''
Created on Nov 9, 2012

@author: ivan
'''

from array import array
import logging
log=logging.getLogger("gdbus")
from gi.repository import Gio, GLib, GObject
from collections import defaultdict
import utils

class DBusProxyWrapper(object): 
    BUS_TYPES={'session':Gio.BusType.SESSION, 'system': Gio.BusType.SYSTEM}
    
    def __init__(self, bus_type, bus_name, object_path, interface, sync_props=False, receive_signals=False):
        self.bus_type=bus_type
        self.bus_name=bus_name
        self.interface=interface
        self.object_path=object_path
        self.sync_props=sync_props
        self.receive_signals=receive_signals
        
        bus_type=self.BUS_TYPES.get(bus_type)
        if not bus_type:
            raise ValueError('Invalid bus type')
        flags=Gio.DBusProxyFlags.DO_NOT_AUTO_START
        if not receive_signals:
            flags|=Gio.DBusProxyFlags.DO_NOT_CONNECT_SIGNALS
        self._proxy=Gio.DBusProxy.new_for_bus_sync(Gio.BusType.SYSTEM, 
                        flags, None,
                        bus_name, object_path,interface, None)
        
        if not self._proxy:
            raise RuntimeError('Cannot load proxy for %s' % interface)
        if receive_signals:
            self._proxy_sig=self._proxy.connect('g-signal', self._receive_signal)
        self._props_proxy=None
        try:
            self._props_proxy=Gio.DBusProxy.new_for_bus_sync(Gio.BusType.SYSTEM, 
                    Gio.DBusProxyFlags.DO_NOT_AUTO_START, None,
                        bus_name, object_path,
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
        for l in self._listeners[signal]:
            #todo - should call with idle? or thread save
            l(*params)
            
    def __getattr__(self, name):
        names=self._proxy.get_cached_property_names()
        if name in names:
            if self.sync_props and hasattr(self, '_props_proxy') and self._props_proxy:
                #log.debug('Getting property %s from remote object %s', name, self.object_path)
                val= self._props_proxy.call_sync('Get', GLib.Variant('(ss)',(self.interface, name)),
                    Gio.DBusCallFlags.NONE, -1, None)
                self._proxy.set_cached_property(name, val)
                return self._unpack_value(val)
            else:
                return self._unpack_value(self._proxy.get_cached_property(name))
        else:
            return getattr(self._proxy,name)
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

NM_DEVICE_TYPE_UNKNOWN = 0
NM_DEVICE_TYPE_ETHERNET = 1
NM_DEVICE_TYPE_WIFI = 2
NM_DEVICE_TYPE_UNUSED1 = 3
NM_DEVICE_TYPE_UNUSED2 = 4
NM_DEVICE_TYPE_BT = 5
NM_DEVICE_TYPE_OLPC_MESH = 6
NM_DEVICE_TYPE_WIMAX = 7
NM_DEVICE_TYPE_MODEM = 8
NM_DEVICE_TYPE_INFINIBAND = 9
NM_DEVICE_TYPE_BOND = 10
NM_DEVICE_TYPE_VLAN = 11

NM_ACTIVE_CONNECTION_STATE_UNKNOWN = 0
NM_ACTIVE_CONNECTION_STATE_ACTIVATING = 1
NM_ACTIVE_CONNECTION_STATE_ACTIVATED = 2
NM_ACTIVE_CONNECTION_STATE_DEACTIVATING = 3
        
class NMError(Exception) : pass       
class NMBase(DBusProxyWrapper):
    #INTERFACE=must specify this class attr in derived classes
    def __init__(self, object_path, **kwargs): 
        super(NMBase,self).__init__("system", 'org.freedesktop.NetworkManager',
                                    object_path, self.INTERFACE, sync_props=True, **kwargs)     
        

        
class NetworkManager (NMBase):
    INTERFACE='org.freedesktop.NetworkManager'
    def __init__(self):
        super(NetworkManager, self).__init__('/org/freedesktop/NetworkManager', receive_signals=True)
        def echo(*args):
            log.debug( "NM Prop.Changes args %s", args)
        self.add_listener('PropertiesChanged', echo)
        
class NetworkManagerMonitor(NetworkManager):  
    def __init__(self):
        super(NetworkManagerMonitor, self).__init__()
        self.pending_connections=[]

    def remove_pending(self):
        for cn in self.pending_connections:
            cn.remove_listener('PropertiedChanged', self.on_conn_state_change)
            cn.disconnect()   
        self.pending_connections=[]
        
    def on_conn_state_change(self, props):
        log.debug('Pending connection state changed to %s', props)
        if props.get('State') and props['State']!=NM_ACTIVE_CONNECTION_STATE_ACTIVATING:
            conns=self.ActiveConnections
            log.debug('Emmitting signal')
            self.fake_signal('__internal__', 'PropertiesChanged',  ({'ActiveConnections':conns},))
    
    def disconnect(self):
        super(NetworkManagerMonitor, self).disconnect()
        self.remove_pending()
            
    def get_default_connection_info(self):
        self.remove_pending()
        connections_list=self.ActiveConnections
        conns= map(lambda path: self.to_object(path, klass=NMConnectionActive),connections_list)
        
        c_vpn,c_default=None, None
        for cn in conns:
            state=cn.State
            #print cn.Uuid, state
            if state != NM_ACTIVE_CONNECTION_STATE_ACTIVATED:
                log.debug('Adding connection %s to pending', cn.get_object_path())
                non_active=self.to_object(cn.get_object_path(),klass=NMConnectionActive, receive_signals=True )
                non_active.add_listener('PropertiesChanged', self.on_conn_state_change)
                self.pending_connections.append(non_active)
                continue
            if cn.Vpn:
                c_vpn=cn
                break
            if cn.Default:
                    c_default=cn
        c=c_vpn or c_default
        if not c:
            log.warn("Cannot get vpn or default connection")
            return None
        
        conn_info={}
        conn_info['vpn']=c.Vpn
        settings=self.to_object(c.Connection, klass=NMConnection).GetSettings()
        type=settings['connection']['type']
        conn_info['type']=type
        conn_info['name']=settings['connection']['id']
        ssid=None
        if type=="802-11-wireless":
            ssid=settings.get(type) and settings.get(type).get('ssid')
            ssid=utils.bytes_to_string(ssid)
        if type=="802-11-wireless" or type=="802-3-ethernet":
            mac=settings.get(type) and settings.get(type).get('mac-address')
            mac=utils.bytes_to_mac(mac)
            if mac:
                conn_info['mac']=mac
        
        ip4_setup=settings.get('ipv4') and settings.get('ipv4').get('method')
            
        devices=c.Devices
        
        if len(devices)>1:
            log.warn('We cannot work with more devices on connection %s, will use first one', 
                     conn_info['name'] )
        if not devices:
            raise NMError('Active connection %s does not have any devices', conn_info['name'])    
            
        device=self.to_object(devices[0], klass=NMDevice)
        
        conn_info['interface']=device.Interface
        ip_addr2=utils.ip4_to_str(device.Ip4Address)
        #conn_info['ip4']=utils.ip4_to_str(device.Ip4Address)
        dev_type=device.DeviceType
        conn_info['device_type']=NM_DEVICE_TYPES_MAP.get(dev_type)[0]
        if dev_type==NM_DEVICE_TYPE_WIFI:
            spec_dev=device.get_specific_device()
            app_id=spec_dev.ActiveAccessPoint
            ap=self.to_object(app_id,  klass=NMAccessPoint)
            try:
                ssid2=utils.bytes_to_string(ap.Ssid)
                if ssid!=ssid2:
                    log.warn("SSIDs differ %s %s", ssid, ssid2)
                conn_info['ssid']=ssid2
            except Exception,e:
                log.warn("ssid error %s",e)
        ip_addr, net_mask= None, None        
        if ip4_setup=='autox':
            setup=self.to_object(device.Dhcp4Config, klass=NMDHCP4Config).Options
            log.debug( 'DHCP Setup %s', setup)
            ip_addr=setup.get('ip_address')
            if ip_addr!=ip_addr2:
                log.error('IP addresses not matching! %s %s', ip_addr2, ip_addr)
                ip_addr=None
            net_mask=setup.get('subnet_mask')
        else:
            setup=self.to_object(device.Ip4Config, klass=NMIP4Config)
            addrs=setup.Addresses
            for a,m,g in addrs:
                a=utils.ip4_to_str(a)
                m=utils.byte_to_mask(m)
                log.debug('IP4 Setup %s, %s', a, m)
                if a==ip_addr2:
                    net_mask=m
                    ip_addr=a
                    break
            if not ip_addr or not net_mask:
                raise NMError('Cannot determine ip net configuration!')
        
        conn_info['ip']=ip_addr
        conn_info['net_mask']=net_mask
        del setup
        return conn_info or None
    
class NMConnectionActive(NMBase):
    INTERFACE='org.freedesktop.NetworkManager.Connection.Active'

       
class NMConnection(NMBase):
    INTERFACE='org.freedesktop.NetworkManager.Settings.Connection'
    
class NMDevice(NMBase):
    INTERFACE='org.freedesktop.NetworkManager.Device'
    
    def get_specific_device(self):
        dev_type=self.DeviceType
        if NM_DEVICE_TYPES_MAP.get(dev_type):
            klass=NM_DEVICE_TYPES_MAP[dev_type][1]
            return self.to_object(self.object_path, klass=klass)
    
    
class NMWired(NMBase):
    INTERFACE='org.freedesktop.NetworkManager.Device.Wired'
    
class NMWireless(NMBase):
    INTERFACE='org.freedesktop.NetworkManager.Device.Wireless'
    
class NMBluetooth(NMBase):
    INTERFACE='org.freedesktop.NetworkManager.Device.Bluetooth'
    
class NMOlpcMesh(NMBase):
    INTERFACE='org.freedesktop.NetworkManager.Device.OlpcMesh'
    
class NMWimax(NMBase):
    INTERFACE='org.freedesktop.NetworkManager.Device.Wimax'
    
class NMModem(NMBase):
    INTERFACE='org.freedesktop.NetworkManager.Device.Modem'
   
class NMAccessPoint(NMBase):
    INTERFACE='org.freedesktop.NetworkManager.AccessPoint'
    
class NMDHCP4Config(NMBase):
    INTERFACE='org.freedesktop.NetworkManager.DHCP4Config'
    
class NMIP4Config(NMBase):
    INTERFACE='org.freedesktop.NetworkManager.IP4Config'

NM_DEVICE_TYPES_MAP={
            NM_DEVICE_TYPE_ETHERNET: ('Wired', NMWired),
            NM_DEVICE_TYPE_WIFI: ('Wireless', NMWireless),
            NM_DEVICE_TYPE_BT: ('Bluetooth', NMBluetooth),
            NM_DEVICE_TYPE_OLPC_MESH: ('OlpcMesh',NMOlpcMesh),
            NM_DEVICE_TYPE_WIMAX: ('Wimax',NMWimax),
            NM_DEVICE_TYPE_MODEM: ('Modem',NMModem),
        }
        
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