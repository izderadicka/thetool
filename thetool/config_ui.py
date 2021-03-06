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
    InstancesListBox, InstancesListDialog, Validator, UiHelper, ActionsBox

SETTINGS_ID='eu.zderadicka.thetool'
NET_SETTINGS_ID=SETTINGS_ID+".network"

        
class NetworkDetailDialog(FormSettingsDialog):
    UI_FILES=['network-detail.ui']
    UI_ROOT='network-detail'
    
    VALUES_MAPPING=(('display-name', 'name', 's'),
                    ('nm-name', 'id', 's'),
                    ('ip-address', 'network-ip', 's'),
                    ('subnet-mask', 'network-mask', 's'))
    def __init__(self, parent, settings, path, nm, new):
        
        self.nm=nm
        self.path=path
        log.debug("Network config for path %s", path)
        settings=settings.get_settings_under(NET_SETTINGS_ID, path)
        FormSettingsDialog.__init__(self, "Network Detail", parent, settings, new)
        actions=None if new else self.settings.get_unpacked('network-actions')
        self.box=ActionsBox("Actions", actions)
        self.ui.get_widget('actions-box').pack_start(self.box,True, True, 0)
        
        
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
    
    def save_all(self):
        super(NetworkDetailDialog, self).save_all()
        self.settings.set_formatted('network-actions', self.box.get_actions(), 'as')


class NetworksHandler(AbstactListHandler):
    
    def __init__(self, settings, nm):
        self.settings=settings
        self.nm=nm
        self.dirty=False
    
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
    
    def create_details_dialog(self,path, name, new):
        return NetworkDetailDialog(self.get_parent_window(), self.settings, path, self.nm, new)    
    
    def update_settings(self):
        self.dirty=True
    
    def update_after_added(self, path, name):
        self.update_settings()
        
    def update_after_edit(self, path, name):
        self.update_settings()
        
    def update_after_delete(self, path, name):
        self.update_settings()
        
    def update_after_dnd(self, form_index, to_index):
        self.update_settings()    
        
          
class NetworksDialog(InstancesListDialog):
    def __init__(self, parent, settings, nm):
        self.handler=NetworksHandler(settings, nm)
        InstancesListDialog.__init__(self, "Known Networks", parent, self.handler, True)

class ActionsHandler(AbstactListHandler):
    
    def __init__(self):
        pass
    
    def get_inital_list(self):
        names=actions.get_actions_list(sorted=True)
        for i,name in enumerate(names):
                yield "%s-%d"%(self.get_path_base(),i),name
    
    def get_path_base(self):
        return 'action'
    
    def create_details_dialog(self,path, name, new):
        return ActionDetailDialog(self.get_parent_window(), actions.get_action(name))    
    
    def update_after_added(self, path, name):
        pass
        
    def update_after_edit(self, path, name):
        pass
        
    def update_after_delete(self, path, name):
        actions.remove_action(name)
        
        
class ActionsDialog(InstancesListDialog):
    def __init__(self, parent):
        self.handler=ActionsHandler()
        InstancesListDialog.__init__(self, "Actions", parent, self.handler)

class AssignActionsDialog(Gtk.Dialog):
    def __init__(self, title, parent, actions): 
        Gtk.Dialog.__init__(self, title, parent, Gtk.DialogFlags.MODAL|Gtk.DialogFlags.DESTROY_WITH_PARENT, (Gtk.STOCK_CLOSE,Gtk.ResponseType.CLOSE))
        self.box=ActionsBox(title, actions)
        self.get_content_area().add(self.box)
    def get_actions(self):
        return self.box.get_actions()
              
        
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
        self.connect('response', self.on_close)
        self.connect('delete-event', lambda x,y:self.hide_on_delete())
    
    def set_netmanager(self,nm):
        self.nm=nm
        
    def on_close(self, dialog, resp_id, data=None):  
        log.debug("Close settings")  
        self.hide()
    def _connect_widgets(self): 
        self.settings.bind('enable-notifications', self.ui.get_widget('enable-notifications'), 'active', 
                      Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind('monitor-networks', self.ui.get_widget('monitor-networks'), 'active', 
                      Gio.SettingsBindFlags.DEFAULT)
        
        self.settings.bind('notify-before-poweroff', self.ui.get_widget('notify-before-poweroff'), 'value',
                           Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind('player-poweroff-timeout', self.ui.get_widget('player-poweroff-timeout'), 'value',
                           Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind('actions-file', self.ui.get_widget('actions-file'), 'text',
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
        if d.handler.dirty:
            nets=d.handler.get_list()
            self.settings.set_formatted('networks', nets, 'as')
            log.debug("Networks changed to %s", nets)
            if hasattr(self,'nm') and self.nm:
                self.nm.init()
                self.nm.reconnect()
        d.destroy()
        
    def on_show_unknown(self, btn):
        d=AssignActionsDialog("Actions for Unknown Net" ,self, self.settings.get_unpacked('unknown-network-actions'))
        d.run()
        self.settings.set_formatted('unknown-network-actions', d.get_actions(), 'as')
        d.destroy()
    
    def on_quick_actions(self, btn):
        d=AssignActionsDialog('Quick Actions',self, self.settings.get_unpacked('quick-actions'))
        d.run()
        self.settings.set_formatted('quick-actions', d.get_actions(), 'as')
        d.destroy()

    def on_define_actions(self, btn):
        d=ActionsDialog(self) 
        d.run()
        d.destroy()  
        
    def on_select_actions_file(self, btn):
        d=Gtk.FileChooserDialog("Select Actions Definition File", self, Gtk.FileChooserAction.OPEN,
         (Gtk.STOCK_CANCEL,Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.ACCEPT))
        current=self.ui.get_widget('actions-file').get_text()
        if current:
            d.set_filename(current)
        response=d.run()
        if response==Gtk.ResponseType.ACCEPT:
            file_name=d.get_filename()
            self.ui.get_widget('actions-file').set_text(file_name)
        d.destroy()
        
    

class ActionDetailDialog(FormDialog):
    UI_FILES=['action-detail.ui']
    UI_ROOT='__action-detail__'
    def __init__(self, parent, action=None):
        self.action=action
        self.params_model=None
        FormDialog.__init__(self, "Action",parent)
        self.type_view.connect("changed", self.on_type_changed)
        self._init_params_view()
        if not self.action:
            self._create_action_from_type()
            self._old_action_name=None
        else:
            self._old_action_name=action.name
        self._load_params()
        self.ui.get_widget('__action-name__').set_text(self.action.name)
        
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
        self._create_action_from_type()
        self._load_params()
    
    def _create_action_from_type(self):
        item=self.type_view.get_active_iter()
        type_name, type_class= self.type_model[item][:]  
        log.debug("New Action of type  %s created", type_name) 
        self.action=type_class('')
        
        
    def _load_params(self):
        desc_label=self.ui.get_widget('description')
        if hasattr(self.action.__class__, 'DESCRIPTION') and self.action.__class__.DESCRIPTION:
            desc_label.set_markup(self.action.__class__.DESCRIPTION)
            desc_label.set_visible(True)
        else:
            desc_label.set_markup(None)
            desc_label.set_visible(False)
            
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
            value = self.action.get_param_as_str(name) 
            error,msg=self._validate_param(name, value)
            self.params_model.append([name, mandatory, type.__name__, 
                    value or '', error, msg ,'#ffc7c7'])
            
        self._enable_submit()
            
    def save_all(self):
        self.action.name=self.ui.get_widget('__action-name__').get_text().decode('UTF-8')
        for row in self.params_model:
            self.action.set_param(row[0],row[3])
        if self._old_action_name:
            actions.remove_action(self._old_action_name, no_save=True)
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
        
    def get_name(self):
        return self.ui.get_widget('__action-name__').get_text()
                
            