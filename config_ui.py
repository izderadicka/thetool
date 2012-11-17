'''
Created on Nov 16, 2012

@author: ivan
'''
import sys
import os
import re
import os.path
import logging
import time
log=logging.getLogger("TheTool.Configuration")
import types
from gi.repository import Gtk, GdkPixbuf, GObject, Gio, GLib, Gdk, Notify

import utils
_curr_dir=os.path.split(__file__)[0]

SETTINGS_ID='eu.zderadicka.thetool'
NET_SETTINGS_ID=SETTINGS_ID+".network"

class Validator(object):
    MSG_MIN_LENGHT="Input must have at least %d characters"
    MSG_MAX_LENGTH="Input may not have more then %d characters"
    MSG_REGEXP="Input must match regular expression %s"
    def __init__(self, entry, min_length=None, max_length=None, allowed_chars=None, regexp=None,
                 on_check=None, no_cb_inittialy=False):
        self.entry=entry
        self.min_length=min_length
        self.max_length=max_length
        self.allowed_chars=allowed_chars
        self.regexp=None
        if regexp:
            self.regexp=re.compile(regexp, re.UNICODE)
        self.on_check=on_check
        self._failures=[]
        self._connected_signals=[]
        self._connect_entry(no_cb_inittialy)
    
    
    def _connect_entry(self, no_cb):
        self.validate(no_cb)
        id=self.entry.connect('changed', self.on_entry_changed)  
        self._connected_signals.append(id) 
        if self.allowed_chars:
            id= self.entry.connect('insert-text', self.on_text_inserted)
            self._connected_signals.append(id)
        
        
    def disconnect(self):
        for sig in self._connected_signals:
            self.entry.disconnect(sig)
         
    def validate(self, no_callbacks=False):
        self._failures=[]
        if self.min_length:
            if len(self.entry.get_text() or '')< self.min_length:
                self.fail(self.MSG_MIN_LENGHT % self.min_length)
        if self.max_length:
            if len(self.entry.get_text() or '')>self.max_length:
                self.fail(self.MSG_MAX_LENGHT % self.max_length)
                
        if self.regexp:
            text=None
            try:
                text=self.entry.get_text().decode('UTF-8')
            except UnicodeError:
                log.error('Invalid input text - not unicode' )
            if text:
                m=self.regexp.match(text)
                if not m:
                    self.fail(self.MSG_REGEXP % self.regexp.pattern)
                
        if self._failures:
            self._display_failed()
            if self.on_check and not no_callbacks:
                self.on_check(False,self.entry)
        else:
            self._reset_failed()
            if self.on_check and not no_callbacks:
                self.on_check(True,self.entry)
            
    def is_valid(self):
        return len(self._failures)==0
    def on_entry_changed(self,entry):     
        self.validate()  
             
    def fail(self, msg):
        self._failures.append(msg)
        
    def _display_failed(self):
        self.entry.set_icon_from_stock(Gtk.EntryIconPosition.SECONDARY, Gtk.STOCK_CANCEL)
        self.entry.set_icon_tooltip_text(Gtk.EntryIconPosition.SECONDARY, '\n'.join(self._failures))
    
    def _reset_failed(self):
        self.entry.set_icon_from_stock(Gtk.EntryIconPosition.SECONDARY, None)
        
    def on_text_inserted(self, entry, new_text, text_lenghth, position):
        log.debug("Limited entry text entered %s", new_text)
        for ch in new_text:
            if ch not in self.allowed_chars:
                self.entry.emit_stop_by_name('insert-text')
                return True

class NetworkDetailDialog(Gtk.Dialog):
    UI_FILES=['network-detail.ui']
    UI_ROOT='network-detail'
    
    VALUES_MAPPING=(('display-name', 'name', 's'),
                    ('nm-name', 'id', 's'),
                    ('ip-address', 'network-ip', 's'),
                    ('subnet-mask', 'network-mask', 's'))
    def __init__(self, parent, settings, path, nm):
        Gtk.Dialog.__init__(self, "Network Detail", parent, Gtk.DialogFlags.MODAL, (Gtk.STOCK_CANCEL,Gtk.ResponseType.CANCEL, Gtk.STOCK_APPLY, Gtk.ResponseType.OK))
        
        log.debug("Network config for path %s", path)
        self.settings=settings.get_settings_under(NET_SETTINGS_ID, path)
        self.nm=nm
        self.ui=UiHelper(self)
        self.path=path
        self.validators=[]
        self.get_content_area().add(self.ui.get_widget(self.UI_ROOT))
        self._load_from_settings()
        self._init_validations()
        
    def _init_validations(self):
        self.add_validator('display-name', min_length=3, max_length=40)
        self.add_validator('nm-name', min_length=1, max_length=40) 
        self.add_validator('ip-address', allowed_chars='0123456789.', regexp=r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$') 
        self.add_validator('subnet-mask', allowed_chars='0123456789.', regexp=r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$') 
        
        
    def add_validator(self,widget_name, min_length=None, max_length=None, allowed_chars=None, regexp=None):
        self.validators.append(Validator(self.ui.get_widget(widget_name), min_length, max_length, 
                                allowed_chars,regexp, on_check=self._enable_submit )) 
        self._enable_submit(None,None)   
    def _enable_submit(self,v,entry_checked):  
        is_ok=True
        for v in self.validators:
            if not v.is_valid():
                is_ok=False
                break
        self.get_widget_for_response(Gtk.ResponseType.OK).set_sensitive(is_ok)
    def _load_from_settings(self):
        for widget, setting, format in self.VALUES_MAPPING:
            if format=='s':
                self.set_text(widget,setting)
        
    def save_all(self): 
        for widget, setting, format in self.VALUES_MAPPING:
            self.save(widget,setting, format)
        
    def save(self, widget,setting, format='s'):  
        self.settings.set_formatted(setting, self.ui.get_widget(widget).get_text(), format)
        
    def set_text(self,widget,setting):
        self.ui.get_widget(widget).set_text(self.settings.get_unpacked(setting))
            
    def on_done(self, btn):
        print 'try prevent'
        return True  
         
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
        
    
    
class NetworksDialog(Gtk.Dialog):
    UI_FILES=['networks.ui']
    UI_ROOT='networks'
    def __init__(self, parent, settings, nm):
        Gtk.Dialog.__init__(self, "Known Networks", parent, Gtk.DialogFlags.MODAL, (Gtk.STOCK_CLOSE,Gtk.ResponseType.CLOSE))
        #self.set_decorations(Gdk.WMDecoration.TITLE)
        self.settings=settings
        self.nm=nm
        self.ui=UiHelper(self)
        self.get_content_area().add(self.ui.get_widget(self.UI_ROOT))
        self._init_ui()
        self.set_list(self.settings.get_unpacked('networks'))
        
    def _init_ui(self):
        self.model=Gtk.ListStore(str,str)
        self.view=self.ui.get_widget('networks-list')  
        self.buttons_for_selected=[self.ui.get_widget(w) for w in('remove_button', 'edit_button')]
        select=self.view.get_selection()
        select.connect("changed", self.on_selection)
        self.view.set_model(self.model)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Name", renderer, text=1)
        self.view.append_column(column)
        self._enable_btns()
    
    def _enable_btns(self):
        _, iter= self.view.get_selection().get_selected()
        status= (iter!=None)
        for b in self.buttons_for_selected:
            b.set_sensitive(status)
    def get_list(self):
        res=[]
        for row in self.model:
            res.append(row[0])  
        return res
    def set_list(self,nets):
        log.debug('Settings Networks to %s', nets)
        for n in nets:
            net_settings=self.settings.get_settings_under(NET_SETTINGS_ID,n)
            name=net_settings.get_unpacked('name')
            if name:
                self.model.append([n,name])
    def update_settings(self):
        nets=self.get_list()
        self.settings.set_formatted('networks', nets, 'as')
        log.debug("Networks changed to %s", nets)
    def on_add(self, btn):
        self.edit_network(new=True)
        
    def edit_network(self, new=False):
        if new:
            path=self._create_path()   
        else: 
            path= self.get_selected_path()
        d=NetworkDetailDialog(self, self.settings, path, self.nm)
        response=d.run()
        if response==Gtk.ResponseType.OK:
            if new:
                self.model.append([d.get_path(),d.get_name()])
                self.update_settings()
            else:
                model, iter=self.view.get_selection().get_selected() 
                model[iter][1]=d.get_name()
            d.save_all()
        d.destroy()
            
    def get_selected_path(self, selection=None):
        if not selection:
            selection=self.view.get_selection()
        model, iter=selection.get_selected()
        if iter:
            return model[iter][0]
            
    def _create_path(self):
        def get_no(n):
            if n:
                n=n.split('-')
                return int(n[1]) if len(n)>1 else 0;
            return 0
        no=1
        all=self.get_list()
        numbers=map(lambda x: get_no(x),all)
        if numbers:
            no=max(numbers)+1
        return 'network-%d'%no
        
    def on_delete(self,btn):
        selection=self.view.get_selection()
        model, item=selection.get_selected()
        if item:
            model.remove(item)
            self.update_settings()
    def on_edit(self, btn):
        path=self.get_selected_path()
        if path:
            self.edit_network()
            self.settings.emit('changed', 'networks')
    def on_selection(self, selection):
        self._enable_btns()
        model,iter=selection.get_selected()
        if iter:
            log.debug("Item selected %s", model[iter])
    
        
        
        
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

        

class UiHelper():
    def __init__(self, for_object):
        self.ui = Gtk.Builder()
        for f in for_object.UI_FILES:
            self.ui.add_from_file(os.path.join(_curr_dir, 'ui', f))
        self.ui.connect_signals(for_object)
    def get_widget(self, name):
        return self.ui.get_object(name)
    
    
class Settings(Gio.Settings):
    DIRECTORY=_curr_dir if _curr_dir.startswith('/home/') else None 
    
    def __new__(cls, schema_id,path=None):
        instance= Settings.__create_instance(schema_id, path)
        instance.DIRECTORY=cls.DIRECTORY
        if cls.DIRECTORY:
            #inject methods from this class
            for m in cls.__dict__:
                
                if type(getattr(cls,m)) is types.MethodType and not m.startswith('__') :
                    log.debug("Injecting method %s %s", m , type(getattr(cls,m)))
                    setattr(instance, m, getattr(cls,m).__get__(instance, cls))
              
            # simulate init
            if cls.__dict__.get('__init__'):
                getattr(cls, '__init__').__get__(instance,cls)(schema_id, path)
        return instance
            
    @classmethod    
    def __create_instance(cls,schema_id, path):
        if cls.DIRECTORY:
            log.debug('Creating instance for settings')
            schema_source=Gio.SettingsSchemaSource.new_from_directory(cls.DIRECTORY, 
                Gio.SettingsSchemaSource.get_default(), False)
            schema=Gio.SettingsSchemaSource.lookup(schema_source, schema_id,False)
            if not schema:
                raise Exception("Cannot get GSettings  schema")
            instance= Gio.Settings.new_full(schema, None, path)
            return instance
        else:
            return Gio.Settings.__new__(cls, schema_id, path)
        
    def __init__(self, schema_id, path=None):
        if not self.DIRECTORY:
            Gio.Settings.__init__(self, schema_id, path)
        log.debug( "Settings initialized")
    def get_unpacked(self, key):
        return self.get_value(key).unpack()
    
    def set_formatted(self, key, value, format):
        self.set_value(key, GLib.Variant(format, value))
        
    def get_settings_under(self, id, sub_path):
        p=self.get_property('path')
        if not p.endswith('/'):
            p+='/'
        p+=sub_path+'/'
        return Settings(id, p)