'''
Created on Nov 16, 2012

@author: ivan
'''
import sys
import logging
log=logging.getLogger("TheTool.Configuration")
from gi.repository import Gtk, Gio, GLib #@UnresolvedImport

import utils
import actions
from ui_base import FormDialog, FormSettingsDialog, AbstactListHandler, \
    InstancesListBox, InstancesListDialog, Validator, UiHelper

SETTINGS_ID='eu.zderadicka.thetool'
NET_SETTINGS_ID=SETTINGS_ID+".network"

        
class NetworkDetailDialog(FormSettingsDialog):
    UI_FILES=['network-detail.ui']
    UI_ROOT='network-detail'
    
    VALUES_MAPPING=(('display-name', 'name', 's'),
                    ('nm-name', 'id', 's'),
                    ('ip-address', 'network-ip', 's'),
                    ('subnet-mask', 'network-mask', 's'))
    def __init__(self, parent, settings, path, nm):
        
        self.nm=nm
        self.path=path
        log.debug("Network config for path %s", path)
        FormSettingsDialog.__init__(self, "Network Detail", parent, 
                settings.get_settings_under(NET_SETTINGS_ID, path))
        
    def init_validations(self):
        self.add_validator('display-name', min_length=3, max_length=40)
        self.add_validator('nm-name', min_length=1, max_length=40) 
        self.add_validator('ip-address', allowed_chars='0123456789.', regexp=r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$') 
        self.add_validator('subnet-mask', allowed_chars='0123456789.', regexp=r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$') 
        
    
            
         
    def on_get_current_net(self, btn):
        active=self.nm.get_default_connection_info()
        if active:
            #{'name': 'Wired connection 1', 'ip': '192.168.1.24', 'net_mask': '255.255.255.0', 'mac': '5c:26:a:4:c1:d3', 'device_type': 'Wired', 'interface': 'eth0', 'vpn': False, 'type': '802-3-ethernet'}
            if not self.ui.get_widget('display-name').get_text():
                self.ui.get_widget('display-name').set_text(active.get('name'))
            self.ui.get_widget('nm-name').set_text(active.get('name'))
            if active.get('device_type')=='Wired' and not active.get('vpn'):
                self.ui.get_widget('ip-address').set_text(active.get('ip'))
                self.ui.get_widget('subnet-mask').set_text(active.get('net_mask'))
    
    def get_name(self):
        return self.ui.get_widget('display-name').get_text()
    
    def get_path(self):
        return self.path


class NetworksHandler(AbstactListHandler):
    
    def __init__(self, settings, nm):
        self.settings=settings
        self.nm=nm
    
    def get_inital_list(self):
        nets=self.settings.get_unpacked('networks')
        log.debug('Settings Networks to %s', nets)
        for n in nets:
            net_settings=self.settings.get_settings_under(NET_SETTINGS_ID,n)
            name=net_settings.get_unpacked('name')
            if name:
                yield n,name
    
    def get_path_base(self):
        return 'network'
    
    def create_details_dialog(self,path):
        return NetworkDetailDialog(self.get_parent_window(), self.settings, path, self.nm)    
    
    def update_settings(self):
        nets=self.get_list()
        self.settings.set_formatted('networks', nets, 'as')
        log.debug("Networks changed to %s", nets)
    
    def update_after_added(self, path):
        self.update_settings()
        
    def update_after_edit(self, path):
        self.settings.emit('changed', 'networks')
        
    def update_after_delete(self, path):
        self.update_settings()
        
           
class NetworksDialog(InstancesListDialog):
    PATH_BASE="network"
    def __init__(self, parent, settings, nm):
        self.handler=NetworksHandler(settings, nm)
        InstancesListDialog.__init__(self, "Known Networks", parent, self.handler)
        
        
class SettingsDialog(Gtk.Dialog ):
    UI_FILES=['settings.ui']
    UI_ROOT='settings'
    def __init__(self, settings, power_actions,nm, parent=None):
        self.power_actions=power_actions
        self.dirty=set()
        self.pending_update_id=None
        self.settings=settings
        Gtk.Dialog.__init__(self, "Settings", parent, Gtk.DialogFlags.MODAL, (Gtk.STOCK_CLOSE,Gtk.ResponseType.CLOSE))
        self.ui=UiHelper(self)
        self.get_content_area().add(self.ui.get_widget(self.UI_ROOT))
        self._connect_widgets()
        self.nm=nm
        
    def _connect_widgets(self): 
        self.settings.bind('enable-notifications', self.ui.get_widget('enable-notifications'), 'active', 
                      Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind('monitor-networks', self.ui.get_widget('monitor-networks'), 'active', 
                      Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind('icon-size-width', self.ui.get_widget('icon_width'), 'value', 
                       Gio.SettingsBindFlags.DEFAULT)
        
        self.settings.bind('icon-size-height', self.ui.get_widget('icon_height'), 'value', 
                       Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind('notify-before-poweroff', self.ui.get_widget('notify-before-poweroff'), 'value',
                           Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind('default-poweroff-timeout', self.ui.get_widget('default-poweroff-timeout'), 'value',
                           Gio.SettingsBindFlags.DEFAULT)
        
        self.ui.get_widget("power-off-intervals").set_text(utils.list_to_string(self.settings.get_unpacked('poweroff-intervals')))
        self._validator_po=Validator(self.ui.get_widget('power-off-intervals'), 
                allowed_chars='0123456789, ', regexp=r'(\d{1,6}\s?,?\s?){1,20}', min_length=1,
                  on_check=self.on_power_off_intervals_changed, no_cb_inittialy=True)
        
        wnames=('shutdown', 'suspend', 'hibernate')
        for name in wnames:
            if self.power_actions.get_action(name).get_active():
                self.ui.get_widget(name).set_active(True)
        for name in wnames:
            self.ui.get_widget(name).connect('toggled', self.on_poweroff_type_activate, name)
            
    def on_poweroff_type_activate(self, item, name):
        if item.get_active():
            log.debug("Power Off radio selected  %s", name)
            self.power_actions.get_action(name).set_active(True)
    def on_power_off_intervals_changed(self, valid, item):
        log.debug("Power Intervals changed  to %s", item.get_text())
        if valid:
            self._plan_update("power-off-intervals")
    def _plan_update(self, item):
        self.dirty.add(item)
        if self.pending_update_id:
            GLib.source_remove(self.pending_update_id)
        self.pending_update_id=GLib.timeout_add(2000, self.do_update)    
    def do_update(self):
        for name in self.dirty:
            log.debug('Syncing data to %s settings', name)
            wgt=self.ui.get_widget(name)
            if name=="power-off-intervals":
                try:
                    list=utils.string_to_list(wgt.get_text()) 
                except Exception, e:
                    log.debug("invalid value of list %s", e)
                    #wgt.override_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(1.0, 0.0, 0.0, 1.0) ) 
                else:
                    #wgt.override_color(Gtk.StateFlags.NORMAL, None)
                    self.settings.set_formatted('poweroff-intervals', list, 'ai') 
        self.dirty.clear()
        self.pending_update_id=None
        return False
    
    def on_show_networks(self, btn):
        log.debug('Showing Networks dialog')
        d=NetworksDialog(self, self.settings, self.nm)
        d.run()
        d.destroy()
        
    def on_show_uknown(self, btn):
        pass

    def on_define_actions(self, btn):
        d=ActionDetailDialog(self) 
        d.run()
        d.save_all()
        d.destroy()  
    

class ActionDetailDialog(FormDialog):
    UI_FILES=['action-detail.ui']
    UI_ROOT='__action-detail__'
    def __init__(self, parent, action=None):
        self.action=action
        self._old_action_name=action.name if action else None
        self.params_model=None
        FormDialog.__init__(self, "Action",parent)
        self.type_view.connect("changed", self.on_type_changed)
        self._init_params_view()
        self.on_type_changed(None)
        
    def _init_params_view(self):
        self.params_view=self.ui.get_widget('__action-params__')
        self._new_params_model()
        r=Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Name", r, text=0)
        self.params_view.append_column(column)
        r=Gtk.CellRendererToggle()
        r.set_activatable(False)
        column = Gtk.TreeViewColumn("Mandatory", r, active=1)
        self.params_view.append_column(column)
        
        r=Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Type", r, text=2)
        self.params_view.append_column(column)
        
        r=Gtk.CellRendererText()
        r.set_property('editable',True)
        column = Gtk.TreeViewColumn("Value (editable)", r, text=3, background_set=4, strikethrough=4, background=6)
        self.params_view.append_column(column)
        r.connect("edited", self.on_property_edited)
        self.params_view.set_tooltip_column(5)
            
    def load_values(self):
        if self.action:
            pass
        
        self._fill_types()
    
    
    def _new_params_model(self):
        self.params_model= Gtk.ListStore(str, bool, str, str, bool, str, str)
        self.params_view.set_model(self.params_model)
            
    def _fill_types(self):
        
        self.type_model=Gtk.ListStore(str,object) 
        self.type_view=self.ui.get_widget('__action-type__')
        if self.action==None:
            for line in actions.get_actions_types() :
                self.type_model.append(line) 
        else:
            self.type_model.append([actions.get_action_type_for_action(self.action), None])
            self.type_view.set_sensitive(False)
        
        self.type_view.set_model(self.type_model)
        renderer_text = Gtk.CellRendererText()
        self.type_view.pack_start(renderer_text, True)
        self.type_view.add_attribute(renderer_text, "text", 0)
        
        if not self.action:
            item=self.type_model.get_iter_first()
            self.type_view.set_active_iter(item)
        
    def init_validations(self):
        self.add_validator('__action-name__', min_length=3) 
        
    def on_property_edited(self,widget, path, text):
        name=self.params_model[path][0]
        error,msg=self._validate_param(name, text)
        self.params_model[path][3]=text 
        self.params_model[path][4]=error
        self.params_model[path][5]=msg
        self._enable_submit()
        
          
    def _validate_param(self, name, value):
        try:
            self.action.validate_param(name,value)
            error=False
            msg='Value is OK' #TODO - Why it is not taking None?
        except actions.ParameterError,e:
            error=True
            msg=str(e)
            
        return error, msg
                
            
    def on_type_changed(self, combo):
        item=self.type_view.get_active_iter()
        type_name, type_class= self.type_model[item][:]  
        log.debug("Action type selected to %s", type_name) 
        self.action=type_class('') 
        self._load_params()
        
    def _load_params(self):
        log.debug("Loading params for action %s", self.action)
        self._new_params_model()
        for params_def in self.action.definition_of_parameters:
            
            name=params_def[0]
            mandatory=params_def[1]
            type=params_def[2]
            allowed_values=None
            if len(params_def)>3:
                allowed_values=params_def[3]
            log.debug('Get param %s %s %s %s', name, mandatory, type, allowed_values)  
            value = self.action.get_param(name) 
            error,msg=self._validate_param(name, value)
            self.params_model.append([name, mandatory, type.__name__, 
                    value or '', error, msg ,'#ffc7c7'])
            
        self._enable_submit()
            
    def save_all(self):
        self.action.name=self.ui.get_widget('__action-name__').get_text().decode('UTF-8')
        for row in self.params_model:
            self.action.set_param(row[0],row[3])
        if self._old_action_name:
            actions.remove_action(self.action, no_save=True)
        actions.add_action(self.action)
    
    def _enable_submit(self,valid=None,entry_checked=None):  
        is_ok=True
        for v in self.validators:
            if not v.is_valid():
                is_ok=False
                break
        if is_ok and self.params_model:
            for row in self.params_model:
                if row[4]:
                    is_ok=False
                    break
        self.get_widget_for_response(Gtk.ResponseType.OK).set_sensitive(is_ok)
                
            