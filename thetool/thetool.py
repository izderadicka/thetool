'''
Created on Nov 10, 2012

@author: ivan
'''
__version__='0.3'

import sys
import os.path
import optparse
import logging
log=logging.getLogger("TheTool")
import time
import math
import functools
from collections import defaultdict
from gi.repository import Gtk, GdkPixbuf, GLib, Gdk, Notify, GObject #@UnresolvedImport

import actions
import gdbus
import netmanager
import utils
from config_ui import UiHelper, SettingsDialog, SETTINGS_ID, NET_SETTINGS_ID
from gsettings import Settings
_curr_dir=os.path.split(__file__)[0]

class DuplicateInstance(Exception): pass

class NetMonitor(object):
    def __init__(self, settings, on_change_cb):
        self.on_change_cb=on_change_cb
        self._known_nets=None
        self._known_net=None
        self.settings=settings
        self._current_net=None
        
    def init(self):
        log.debug("Loading nets NetMonitor")
        self._known_nets=defaultdict(lambda: dict())
        for path in self.settings.get_unpacked('networks'):
            try:
                net_details=self.settings.get_settings_under(NET_SETTINGS_ID, path)
                self._known_nets[net_details.get_unpacked('id')][path]=\
                                                    (net_details.get_unpacked('name'),
                                                     net_details.get_unpacked('network-ip'),
                                                    net_details.get_unpacked('network-mask'))
            except:
                log.warn('Cannot get net settings for path %s', path)
                
    def start(self):
        log.debug('Starting NetMonitor')
        self.init()
        self.nm=netmanager.NetworkManagerMonitor()
        self.nm.add_listener('PropertiesChanged', self.on_network_changed)
        self._current_net=None
        self._known_net=None
        self.on_network_changed({'ActiveConnections':True})
        
    def reconnect(self, only_if_unknown=False):
        if only_if_unknown and self.known_net:
            return
        log.debug("Reconnecting NetMonitor")
        self._current_net=None
        self.on_network_changed({'ActiveConnections':True})
   
    def stop(self):   
        log.debug('Stoping NetMonitor')
        if hasattr(self,'nm') and self.nm:
            try:
                self.nm.remove_listener('PropertiesChanged', self.on_network_changed)    
            except:
                log.exception('Cannot remove NM listener')
            self.nm.disconnect()
        self.nm=None    
        self._current_net=None
        self._known_nets=None
        self._known_net=None
    
    def _match_net(self, net, name, ip, mask):
        if net.get('name')!=name:
            return False
        if net.get('device_type')=='Wired' and ip and mask:
            return utils.match_ip(net.get('ip'),ip, mask)
        return True
        
    def _get_known(self, net):
        name=net.get('name')
        known=self._known_nets.get(name)
        if known:
            for path in known:
                known_name, ip, mask= known[path]
                if self._match_net(net, name, ip, mask):
                    return path
        
    def on_network_changed(self, props):
        if props.has_key('ActiveConnections'):
            net=self.nm.get_default_connection_info()
            if net:
                log.debug('Def. Network changed to: %s',  net)
                name=net.get('name')
                if  self._current_net and self._match_net(net, *self._current_net):
                    return
                self._current_net=(name, net.get('ip'), net.get('net_mask'))
                self._known_net=self._get_known(net)
                self.on_change_cb(self._known_net)
    def get_default_connection_info(self):
        return self.nm.get_default_connection_info()
    

class TheTool(Gtk.Application):
    UI_FILES=[]
    STATUS_IDLE, STATUS_POWER_OFF_TIMER= "Idle", "Will Power Off"
    NAME="TheTool"
    def __init__(self):
        Gtk.Application.__init__(self, application_id=SETTINGS_ID)
        self.register(None)
        already_registered=self.get_is_remote()
        if already_registered:
            raise DuplicateInstance
        
        self._init_settings()
        self.icon_normal=GdkPixbuf.Pixbuf.new_from_file(os.path.join(_curr_dir, 'pics', 'knife-grey.png'))
        self.icon_power_off=GdkPixbuf.Pixbuf.new_from_file(os.path.join(_curr_dir, 'pics', 'knife-red.png'))
        self.tray_icon=Gtk.StatusIcon()
        self.tray_icon.set_visible(True)
        self.tray_icon.set_title("TheTool")
        self.tray_icon.connect('popup-menu', self.show_menu)
        self.tray_icon.connect('activate', self.activate)
        #self.tray_icon.connect('button-press-event', self.on_tray_icon_clicked)
        self._define_actions()
        self._build_menus()
        self.ui=UiHelper(self)
        self._cancel_power_off()
        self._load_actions()
        self._start_nm()
        
        
    def set_tooltip(self, status, message=None): 
        tt=self.NAME+" - %s" 
        if message:
            tt=tt+"- %s" 
            tt=tt% (status,message)
        else:
            tt=tt%status
        self.tray_icon.set_tooltip_text(tt)
        
        
    def _build_menus(self):    
        menu_manager=Gtk.UIManager()
        menu_manager.insert_action_group(self.core_actions)
        menu_manager.insert_action_group(self.power_type_actions)
        menu_manager.add_ui_from_file(os.path.join(_curr_dir, 'ui', 'menus.xml'))
        self.menu_manager=menu_manager
        self.popup=menu_manager.get_widget('/popup')
        self._build_po_menu()
        self._build_actions_menu()
        
    def _build_po_menu(self):
        po_item=self.menu_manager.get_widget('/popup/power_menu/')
        power_off_menu=po_item.get_submenu()
        #remove default Empty child
        power_off_menu.foreach(lambda x,_: power_off_menu.remove(x), None)
        intervals=self.settings.get_unpacked('poweroff-intervals')
        for interval in intervals:
            item=Gtk.MenuItem("%d mins"%interval)
            item.connect('activate',self.on_power_off_action, interval)
            power_off_menu.add(item)
        power_off_menu.show_all()
        po_item.set_visible(True)
        
    def _build_actions_menu(self):
        qa_item=self.menu_manager.get_widget('/popup/actions_menu/')
        qa_menu=qa_item.get_submenu()
        #remove default Empty child
        qa_menu.foreach(lambda x,_: qa_menu.remove(x), None)
        actions_list=self.settings.get_unpacked('quick-actions')
        for a in actions_list:
            item=Gtk.MenuItem(a)
            item.connect('activate',self.on_quick_action, a)
            qa_menu.add(item)
        if actions_list:
            qa_menu.show_all()
            qa_item.set_visible(True)
        else:
            qa_item.set_visible(False)
        
    def _define_actions(self):
        ca=Gtk.ActionGroup('core_actions')
        
        ca.add_actions([('dummy', None, 'dummy', None, None, None ),
                        ('about_action', Gtk.STOCK_ABOUT, None, None, None, 
                        self.on_about_action_activate),
                       ('quit_action', Gtk.STOCK_QUIT, None, None, None,
                        self.on_quit_action_activate),
                        ('settings_action', None, 'Settings ...', None, None,
                         self.on_settings_action_activate),
                        ('monitor_action', None, 'Turn Off Monitor Now', None, None,
                         self.on_monitor_action_activate),
                        ('power_menu_action', None, 'Power Down In ...', None, None, None),
                        ('actions_menu_action', None, 'Quick Actions ...', None, None, None),
                        ('power_off_type_action', None, 'Power Off Type', None, None, None)
                       ])
        action1=Gtk.Action('cancel_power_off_action', 'Cancel Power Down', None, None)
        action1.connect('activate', self.on_cancel_power_off_action)
        ca.add_action(action1)
        self.core_actions=ca
        
        
        pt=Gtk.ActionGroup('power_types_actions')
        action=Gtk.RadioAction("shutdown", "Shut Down", None, None, 1)
        pt.add_action(action)
        action2=Gtk.RadioAction("suspend", "Suspend", None, None, 2)
        action2.join_group(action)
        pt.add_action(action2)
        action3=Gtk.RadioAction("hibernate", "Hibernate", None, None, 3)
        action3.join_group(action)
        pt.add_action(action3)
        curr_type=self.settings.get_unpacked('poweroff-types')
        pt.get_action(curr_type).set_active(True)
        action.connect('activate', self.on_power_type_activated, "shutdown")
        action2.connect('activate', self.on_power_type_activated, "suspend")
        action3.connect('activate', self.on_power_type_activated, "hibernate")
        self.power_type_actions=pt
        
    def _start_nm(self):
        if self.settings.get_unpacked('monitor-networks'):
            self.nm=NetMonitor(self.settings, self.on_network_changed)
            self.nm.start()
        else:
            if hasattr(self,'nm') and self.nm:
                self.nm.stop()
            self.nm=None
            
    
    def _load_actions(self):
        actions.ACTIONS_FILE=self.settings.get_unpacked('actions-file')
        actions.load()
        
        
    def main(self):
        GObject.threads_init()
        Gdk.threads_init()
        
        try:
            Gtk.main()
        except KeyboardInterrupt:
            Gtk.main_quit()
        Notify.uninit()
        
    def show_menu(self, tray_icon, button, activate_time, user_data=None):  
        def pos(menu, icon): 
            p= Gtk.StatusIcon.position_menu(menu, icon)
            return p
        log.debug( 'Menu button=%s, time=%s', button, activate_time)
        self.popup.popup(None, None, pos, tray_icon, button, activate_time )
     
    def activate(self, tray_icon, user_data=None):   
        log.debug('Activate')
        if self.timer_id:
            self.on_cancel_power_off_action(None)
        else:
            self.on_power_off_action(None, self.settings.get_unpacked('default-poweroff-timeout'))
            
        
    def _init_settings(self):
        self.settings=Settings(SETTINGS_ID, '/eu/zderadicka/thetool/')
        self.settings.connect("changed", self.on_settings_changed)
        
    def set_icon(self):
        width,height=self.settings.get_unpacked('icon-size-width'), \
                    self.settings.get_unpacked('icon-size-height')
        icon=self.current_icon.scale_simple(width,height, GdkPixbuf.InterpType.NEAREST)
        self.tray_icon.set_from_pixbuf(icon)
        
    def on_quit_action_activate(self, action):
        log.debug('Quiting')
        if hasattr(self,'open_settings') and self.open_settings:
            self.open_settings.destroy()
        Gtk.main_quit()
    def on_about_action_activate(self, action):
        log.debug('About Action')
        d=Gtk.AboutDialog()
        d.set_program_name(self.NAME)
        d.set_version(__version__)
        d.set_copyright('Ivan')
        d.set_license('GPL v3 - http://www.gnu.org/licenses/gpl.html')
        d.set_website('http://zderadicka.eu/thetool-quick-actions-for-desktop/')
        d.set_comments("""The Tool to do some quick 
actions on your desktop
like schedule power off ...
Thanks to Gnome Team for great GUI libraries
Linux desktop rocks! (most of the time:)""")
        d.set_logo(self.icon_normal)
        res=d.run()
        d.hide()
    def on_settings_action_activate(self, action):
        log.debug('Showing Settings')
        
        dialog=SettingsDialog(self.settings, self.power_type_actions, self.nm)
        self.open_settings=dialog
        dialog.run()
        dialog.destroy()
        self.open_settings=None
    def on_monitor_action_activate(self, action):
        def turn_off():
            os.system('xset dpms force off')
            return False
        timer_id=GObject.timeout_add(1000,turn_off)
        
    def on_power_off_action(self, item, interval):
        log.debug("Will power off in %d mins", interval)
        self.start_power_off(interval)
        
    def on_quick_action(self, item, action):
        log.debug("Quick action %s initiated", action)
        actions.ActionsRunner([action], 
                              self._notify_failed_action,
                              False).start()
    
    def _notify_failed_action(self, ok, failed):  
        if failed:
            action, error= failed[0]
            self.send_notification("Action %s <b>failed</b> with error %s" % (action,error))
        
    def on_power_type_activated(self, action, name):
        if action.get_active():
            log.debug("Power Off Type changed to %s", name)
            self.settings.set_string('poweroff-types',name)
            
    def on_settings_changed(self, settings, key, data=None):
        log.debug( "Setting changed %s", key)
        if key=='poweroff-intervals':
            self._build_po_menu()
        elif key.startswith("icon-size-"):
            self.set_icon()
        elif key=="monitor-networks":
            self._start_nm()
        elif key=="actions-file":
            self._load_actions()
        elif key=="quick-actions":
            self._build_actions_menu()
            
            
    def start_power_off(self, mins):
        if self.timer_id:
            GObject.source_remove(self.timer_id)
        
        self.time_to_power_off=time.time()+mins*60
        self.timer_id=GObject.timeout_add(6000, self.timeout_ticks)
        self.set_tooltip(self.STATUS_POWER_OFF_TIMER, "in %d mins" % mins)
        self.send_notification("Will Power Off In %d Minutes"%mins)
        self.current_icon=self.icon_power_off
        self.core_actions.get_action('cancel_power_off_action').set_visible(True)
        self.set_icon()
        
    def timeout_ticks(self):
        log.debug('Power off timeout running')
        remaining=self.time_to_power_off-time.time()
        if remaining <= 0:
            self.power_off()
            return False
        remaining=int(math.ceil(remaining/60))
        self.set_tooltip(self.STATUS_POWER_OFF_TIMER, "in %d mins" % remaining)
        if remaining <= self.settings.get_unpacked('notify-before-poweroff') and \
            not self.power_off_notification_sent:
            self.send_notification("Last Warning - Will Power Off in %d Minutes"% remaining)
            self.power_off_notification_sent=True
        return True
    
    def _cancel_power_off(self):  
        self.timer_id=None
        self.time_to_power_off=None
        self.set_tooltip(self.STATUS_IDLE)
        self.current_icon=self.icon_normal
        self.set_icon()
        self.core_actions.get_action('cancel_power_off_action').set_visible(False)   
        self.power_off_notification_sent=False
          
    def power_off(self):
        log.debug('Powering Off Now')
        self._cancel_power_off()
        power_off_type=self.settings.get_unpacked('poweroff-types')
        gdbus.power_off(power_off_type)
        
    def on_cancel_power_off_action(self, action):
        log.debug('Canceling Power Off')
        GObject.source_remove(self.timer_id)
        self._cancel_power_off()

    def on_tray_icon_clicked(self, icon, event):
        log.debug("Button clicked on tray icon button:%d, time: %d", event.button, event.time)
        #for now show menu also on button1
        if event.button==1:
            self.popup.popup(None, None, None, None, event.button, event.time )
            
    def send_notification(self, message):
        if not self.settings.get_unpacked('enable-notifications'):
            return
        if not Notify.is_initted ():
            Notify.init(self.NAME)
        notification = Notify.Notification.new(
        self.NAME,
        message,
        None# 'dialog-information'
        )
        notification.set_image_from_pixbuf(self.icon_normal)
        notification.show()
        
    def on_network_changed(self, path):
        if path:
            net_settings=self.settings.get_settings_under(NET_SETTINGS_ID, path)
            name=net_settings.get_unpacked('name')
            log.debug("Connected to known net %s",name)
            actions_list=net_settings.get_unpacked('network-actions')
            if actions_list:
                actions.ActionsRunner(actions_list, 
                                      functools.partial(self.notify_network, name),
                                      False).start()
            else:
                self.notify_network(name)                     
            
        else:
            log.debug("Connected to unknown net")
            actions_list=self.settings.get_unpacked('unknown-network-actions')
            if actions_list:
                actions.ActionsRunner(actions_list, 
                                      functools.partial(self.notify_network, None),
                                      False).start()
            else:
                self.notify_network(None)   
            
            
    def notify_network(self, name, ok=[], failed=[]):
        if name:
            msg=" Network %s" %name
        else:
            msg="Network Unknown"
        
        if ok:
            msg+=" (%s)" %', '.join(ok)
        if failed:
            failures=map(lambda x: str(x), failed)
            msg+="/n<b>Errors:</b> %s" % ', '.join(failures)
            
        self.send_notification(msg)


def main(args=None): 
               
    op=optparse.OptionParser()
    op.add_option('-d', '--debug', action="store_true", help="Debug loggin on")
    options, args= op.parse_args(args)
    if options.debug:
        logging.basicConfig(level=logging.DEBUG)
        logging.getLogger('TheTool.GSettings').setLevel(logging.INFO)
        #logging.getLogger('gdbus').setLevel(logging.INFO)
    actions.load_plugins()
    try:
        tool=TheTool()
    except DuplicateInstance:
        msg='Another instance of this applications is already running'
        print msg
        log.error('Another instance of this applications is already running')
        sys.exit(1)
    tool.main()

if __name__=='__main__':
        main()