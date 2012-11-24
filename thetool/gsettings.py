'''
Created on Nov 20, 2012

@author: ivan
'''

import os.path
import logging
log=logging.getLogger("TheTool.GSettings")
import types
from gi.repository import  Gio, GLib #@UnresolvedImport

_curr_dir=os.path.split(__file__)[0]


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
    