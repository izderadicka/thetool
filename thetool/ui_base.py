'''
Created on Nov 20, 2012

@author: ivan
'''
import sys
import re
import os.path
import logging
log=logging.getLogger("TheTool.UIBase")
from gi.repository import Gtk #@UnresolvedImport

_curr_dir=os.path.split(__file__)[0]

import actions

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
            
class FormDialog(Gtk.Dialog):
    def __init__(self, title, parent, new=False):
        Gtk.Dialog.__init__(self,title, parent, 
                Gtk.DialogFlags.MODAL|Gtk.DialogFlags.DESTROY_WITH_PARENT, 
                (Gtk.STOCK_CANCEL,Gtk.ResponseType.CANCEL, Gtk.STOCK_APPLY, Gtk.ResponseType.OK))
        self.ui=UiHelper(self)
        self.validators=[]
        self.get_content_area().add(self.ui.get_widget(self.UI_ROOT))
        if not new:
            self.load_values()
        self.init_validations()
        
    def load_values(self):
        raise NotImplemented
    
    def init_validations(self):
        raise NotImplemented
    
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
    
    def get_name(self):
        return self.ui.get_widget('name').get_text()
    
    def save_all(self):
        raise NotImplementedError()
        
class FormSettingsDialog(FormDialog):
    #VALUES_MAPPING=(('widget-name', 'setting-name', 'seting type string - like s as b ...'),
    def __init__(self, title, parent, settings, new=False):
        self.settings=settings 
        FormDialog.__init__(self, title, parent, new)
        
        
    def load_values(self):
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


class UiHelper():
    def __init__(self, for_object):
        self.ui = Gtk.Builder()
        for f in for_object.UI_FILES:
            self.ui.add_from_file(os.path.join(_curr_dir, 'ui', f))
        self.ui.connect_signals(for_object)
    def get_widget(self, name):
        return self.ui.get_object(name)
            
    
class AbstactListHandler(object):
    
    def get_inital_list(self):
        raise NotImplementedError()
    
    def get_path_base(self):
        return 'item'
    
    def create_details_dialog(self, path, name, new):
        raise NotImplementedError()
    
    def update_after_added(self, path, name):
        raise NotImplementedError()
    
    def update_after_edit(self, path, name):
        pass
    
    def update_after_delete(self, path, name):
        raise NotImplementedError()
    
    def update_after_dnd(self, from_index, to_index):
        pass
    
    def attach_to(self, widget):
        self.widget=widget
        
    def get_list(self):
        if not hasattr(self,'widget'):
            raise Exception('Not attached to widget!')
        res=[]
        for row in self.widget.model:
            res.append(row[0])  
        return res
    
    def get_parent_window(self):
        parent=self.widget   
        while parent is not None and not isinstance(parent, Gtk.Window): 
            parent=parent.get_parent()  
        return parent

class ActionsBox(Gtk.VBox):  
    UI_FILES=['actions_list.ui']   
    UI_ROOT='actions-ui'
    NOT_SELECTED='<Choose Action>'
    def __init__(self, title, actions=None):   
        Gtk.VBox.__init__(self,False,0)
        self.ui=UiHelper(self)
        self.pack_start(self.ui.get_widget(self.UI_ROOT), True, True, 0)
        if title:
            self.ui.get_widget('title-label').set_label(title)  
            self.ui.get_widget('title-label').set_visible(True)
        self.actions=actions
        self._init_ui()
        self.show_all()
        self._enable_delete()
        if actions:
            self.set_actions(actions)
        
    def _init_ui(self):  
        self.model=Gtk.ListStore(str)
        self.view=self.ui.get_widget('actions-view')
        self.view.set_model(self.model)
        self.view.set_reorderable(True)
        all_actions_model = Gtk.ListStore(str)
        for a in actions.get_actions_list(True):
            all_actions_model.append([a])
            
        renderer_combo = Gtk.CellRendererCombo()
        renderer_combo.set_property("editable", True)
        renderer_combo.set_property("model", all_actions_model)
        renderer_combo.set_property("text-column", 0)
        renderer_combo.set_property("has-entry", False)
        renderer_combo.connect("edited", self.on_action_edited)
        
        column=Gtk.TreeViewColumn("Actions", renderer_combo, text=0)
        self.view.append_column(column)
        
        select=self.view.get_selection()
        select.connect("changed", self.on_selection)
        
    def on_action_edited(self, widget, path, text):
        self.model[path][0]=text
    
    def on_add(self, btn):
        log.debug('Item added')
        item=self.model.append([self.NOT_SELECTED])
        self.view.get_selection().select_iter(item)
        
    def on_delete(self,btn):
        
        selection=self.view.get_selection()
        model, item=selection.get_selected()
        if item:
            log.debug('Deleting Item %s', model.get_path(item).to_string())
            model.remove(item)
            
    def _enable_delete(self):
        _, iter= self.view.get_selection().get_selected()
        status= (iter!=None)
        self.ui.get_widget('delete-button').set_sensitive(status)
        
    def on_selection(self, selection):
        self._enable_delete()
        
    def get_actions(self):
        actions_list=[]
        for row in self.model:
            name=row[0]
            if name and name !=self.NOT_SELECTED:
                actions_list.append(name)
        return actions_list
    
    def set_actions(self, actions_list):
        for a in actions_list:
            if actions.exists(a):
                self.model.append([a])
        
        
class InstancesListBox(Gtk.VBox):
    UI_FILES=['items_list.ui']
    UI_ROOT='list-ui'

    def __init__(self, title, handler, dnd=False):
        Gtk.VBox.__init__(self,False,0)
        self.dnd=dnd
        self.dnd_started=None
        self.ui=UiHelper(self)
        self.pack_start(self.ui.get_widget(self.UI_ROOT), True, True, 0)
        if title:
            self.ui.get_widget('title-label').set_label(title)
        self.handler=handler
        self.handler.attach_to(self)
        self._init_ui()
        self.set_list()
        self._connect_signals()
        self.show_all()
      
    def set_list(self):
        for path, name in self.handler.get_inital_list():
            self.model.append([path,name])
            
            
    def _init_ui(self):
        self.model=Gtk.ListStore(str,str)
        self.view=self.ui.get_widget('items-list')  
        self.view.set_reorderable(self.dnd)
        self.buttons_for_selected=[self.ui.get_widget(w) for w in('remove_button', 'edit_button')]
        self.view.set_model(self.model)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Name", renderer, text=1)
        self.view.append_column(column)
        self._enable_btns()
    def on_row_inserted(self, model, path, iter):
        pathi,name=model[iter][:]
        if pathi==None and name==None:
            log.debug("possible DND on row %s", path.to_string())
            self.dnd_started=path.to_string()
        else:
            log.debug("Row inserted %s %s", path.to_string(), [path, name])
            self.dnd_start=False
    def  on_row_deleted(self, model, path):
        if self.dnd_started !=None:
            self.handler.update_after_dnd(path.to_string(), self.dnd_started)
            log.debug("DND from %s to %s", path.to_string(), self.dnd_started )
        else:
            log.debug("Row deleted %s", path.to_string())
        self.dnd_started=None
        
    def _connect_signals(self):
        self.model.connect('row-inserted', self.on_row_inserted)
        self.model.connect('row-deleted', self.on_row_deleted)
        self.view.connect('row-activated', self.on_row_activated)
        select=self.view.get_selection()
        select.connect("changed", self.on_selection)
    def _enable_btns(self):
        _, iter= self.view.get_selection().get_selected()
        status= (iter!=None)
        for b in self.buttons_for_selected:
            b.set_sensitive(status)
            
    def on_add(self, btn):
        self.edit_item(new=True)
        
    def edit_item(self, new=False, path=None, name=None):
        if new:
            path=self._create_path()   
            name=None
        elif not path: 
            path, name= self.get_selected_item()
        d=self.handler.create_details_dialog(path, name, new)
        response=d.run()
        if response==Gtk.ResponseType.OK:
            if new:
                self.model.append([path,d.get_name()])
                self.handler.update_after_added(path,d.get_name())
            else:
                model, iter=self.view.get_selection().get_selected() 
                model[iter][1]=d.get_name()
                self.handler.update_after_edit(path,d.get_name())
            d.save_all()
        d.destroy()
            
    def get_selected_item(self, selection=None):
        if not selection:
            selection=self.view.get_selection()
        model, iter=selection.get_selected()
        if iter:
            return model[iter][:]
            
    def _create_path(self):
        def get_no(n):
            if n:
                n=n.split('-')
                return int(n[1]) if len(n)>1 else 0;
            return 0
        no=1
        all=[row[0] for row in self.model]
        numbers=map(lambda x: get_no(x),all)
        if numbers:
            no=max(numbers)+1
        return '%s-%d'%(self.handler.get_path_base(),no)
        
    def on_delete(self,btn):
        selection=self.view.get_selection()
        model, item=selection.get_selected()
        if item:
            path, name=model[item][:]
            model.remove(item)
            self.handler.update_after_delete(path, name)
            
    def on_edit(self, btn):
        path, _=self.get_selected_item()
        if path:
            self.edit_item()
            
    def on_selection(self, selection):
        self._enable_btns()
        model,iter=selection.get_selected()
        if iter:
            log.debug("Item selected %s", model[iter][:])
            
    def on_row_activated(self, view, row_path, column):
        item =self.model.get_iter(row_path)
        self.view.get_selection().select_path(row_path)
        if  item:
            self.edit_item(False, path=self.model[item][0], name=self.model[item][1])
    
        
class InstancesListDialog(Gtk.Dialog):    
   
    def __init__(self, title, parent, handler, dnd=False):
        Gtk.Dialog.__init__(self, title, parent, Gtk.DialogFlags.MODAL|Gtk.DialogFlags.DESTROY_WITH_PARENT, (Gtk.STOCK_CLOSE,Gtk.ResponseType.CLOSE))
        self.box=InstancesListBox(title, handler, dnd)
        self.get_content_area().add(self.box)
        
            