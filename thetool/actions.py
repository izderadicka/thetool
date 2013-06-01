'''
Created on Nov 17, 2012

@author: ivan
'''

import json
import re
import types
import logging
import os
import os.path
import threading

log=logging.getLogger('TheTool - Actions')

ACTIONS_FILE=os.path.expanduser('~/.config/thetool/actions.json')
PLUGIN_DIRS=(os.path.expanduser('~/.config/thetool/actions'),
             os.path.join(os.path.dirname(__file__),'actions'))
_known_actions_types={}
_actions={}

from gi.repository import GObject #@UnresolvedImport

def load_plugins():
    for folder in PLUGIN_DIRS:
        if not os.path.exists(folder):
            continue
        files=os.listdir(folder)
        for f in files:
            _,ext=os.path.splitext(f)
            if ext=='.py':
                f=os.path.join(folder,f)
                try:
                    with file(f, 'rb') as src:
                        exec(src.read(), globals(), globals())
                        log.debug('Loaded plugin %s',f )
                except:
                    log.exception("Error Loading plugin %s", f)
                    

def save():
    file_path=os.path.dirname(ACTIONS_FILE)
    if not os.path.exists(file_path):
        os.makedirs(file_path)
    with file(ACTIONS_FILE, 'wb') as f:
        dump(f,_actions)
        
def load():
    global _actions
    if os.path.exists(ACTIONS_FILE):
        with file(ACTIONS_FILE, 'rb') as f:
            s=f.read()
            new_actions=loads(s)
            _actions=new_actions
    else:
        log.warn("Actions file %s does not exist", ACTIONS_FILE)
        _actions={}
            
def register_type(klass, name):
    _known_actions_types[name]=klass
    
def add_action(action, dont_save=False):
    _actions[action.name]=action
    if not dont_save:
        save()
    
def exists(name):
    return _actions.has_key(name)
    
def remove_action(action, no_save=False):
    if isinstance(action, basestring):
        del _actions[action]
    elif isinstance(action, Action):
        del _actions[action.name]
    if not no_save:
        save()
        
def get_actions_list(sorted=True):
    actions=_actions.keys()
    if sorted:
        actions.sort()
    return actions

def get_action(name):
    if not name:
        return None
    return _actions.get(name)
        
def get_actions_types():
    return [(n, _known_actions_types[n]) for n  in _known_actions_types]

def get_action_type_for_action(action):
    for k in _known_actions_types:
        if action.__class__ == _known_actions_types[k]:
            return k
    
class Serializer(json.JSONEncoder):
    def default(self,o):
        if  isinstance(o, Action):
            return {'__action__': str(o.__class__.__name__), 'name':o._name, 'parameters':o._params}
        return json.JSONEncoder.default(self,o)
    

    
        
def dumps(o):
    return Serializer().encode(o)

def dump(file,o):
    for chunk in Serializer().iterencode(o):
        file.write(chunk)
def loads(s):
    def create_action(o):
        if isinstance(o, dict) and o.has_key('__action__'):
            klass=globals().get(o['__action__'])
            if klass:
                action=klass(o['name'])
                action._params=o['parameters']
                return action
            else:
                return o
        return o
    ds=json.JSONDecoder(object_hook=create_action)
    return ds.decode(s)
    
class ParameterError(Exception): pass
class Action(object):
    PARAMS_DEFINITION= None#('name' ,  True/False <Mandatory> -,  str <type - python type), ...)
    DESCRIPTION=None
    def __init__(self, name):
        self._name=name
        self._params={}
        
    
    @property
    def definition_of_parameters(self):
        return self.PARAMS_DEFINITION
    
    @property
    def parameters(self):
        params=[]
        for definition in self.PARAMS_DEFINITION:
            name=definition[0]
            params.append((name, self._params.get(name)))
        return params
    
    
    def _get_name(self):
        return self._name
    def _set_name(self, val):
        if not val:
            raise ValueError('Name cannot be empty')
        self._name=val
    name=property(_get_name, _set_name)
        
    
    def set_param(self, name, value):
        validated_value=self.validate_param(name, value)
        self._params[name]=validated_value
        
    def get_param(self, name):
        return self._params.get(name)
    
    def get_param_as_str(self,name):
        type,mandatory,allowed_values= self.get_param_definition(name)
        val=self.get_param(name)
        if val==None:
            return None
        if isinstance(type, basestring):
            return val
        elif type in (list,tuple):
            return ', '.join(val)
        elif type==dict:
            repr=[k+':'+val[k] for k in val]
            return ', '.join(repr)
        else:
            return str(val)
        
        
    def get_param_definition(self, name):   
        type,mandatory,allowed_values= None, None, None
        for param_def in self.definition_of_parameters:
            if name==param_def[0]:
                type=param_def[2]
                mandatory=param_def[1]
                allowed_values= len(param_def)>3 and param_def[3]
                break
        if not type:
            raise ValueError("Invalid param name %s"%name)   
        return  type,mandatory,allowed_values
        
    def validate_param(self, name, value):
        type,mandatory,allowed_values= self.get_param_definition(name)
        for param_def in self.definition_of_parameters:
            if name==param_def[0]:
                type=param_def[2]
                mandatory=param_def[1]
                allowed_values= len(param_def)>3 and param_def[3]
                break
        if not type:
            raise ValueError("Invalid param name %s"%name)        
        if mandatory and not value:
            raise ParameterError("Parameter must have value")
        if value is None:
            return None
        
        validated_value=value
        if type==bool:
            yes=('1', 'y','yes','true','on' )
            no=('0', 'n', 'no', 'false', 'off')
            if value.lower() in yes:
                validated_value= True
            elif not value or value.lower() in no:
                validated_value= False
            else:
                raise ParameterError('Value %s is not boolean representation' % value)
            
        elif type in (int, float):
            try:
                validated_value=type(value)
            except Exception, e:
                log.debug("Parameter %s Error - value %s has error %s" % (name,value,e))
                raise ParameterError('Value %s is not number representation' % value)
        elif type in (list,tuple):
            validated_value=filter(lambda n: n, map(lambda n: n.strip(),value.split(',')))
            if not validated_value and mandatory:
                raise ParameterError("List must have at least one item")
        
        elif type == dict:
            d={}
            pairs=value.split(',')
            for p in pairs:
                p=p.split(':')
                if len(p)!=2:
                    raise ParameterError("Value is not simple dictionary - key1:val2, key2,val2 ...")
                key,val= p[0].strip(), p[1].strip()
                if not key or not val:
                    raise ParameterError("Empty key or value not allowed")
                d[key]=val
            if not d and mandatory:
                raise ParameterError("Dictionary must have at least one item")
            validated_value=d
            
        if allowed_values and  isinstance(allowed_values, (list, tuple)) and \
               type in (str, unicode, basestring, int):
            if validated_value not in allowed_values:
                raise ParameterError('Value not in allowed values %s' % str( allowed_values))
            
        elif allowed_values and isinstance(allowed_values, (list, tuple)) and \
               type in (list, tuple):
            for i in validated_value:
                if i not in allowed_values:
                    raise ParameterError('Value item %s not in allowed values %s' % (i,allowed_values))
                
        elif allowed_values and hasattr(allowed_values, 'pattern') and hasattr(allowed_values, 'match') and \
               type in (str, unicode, basestring):
            if not allowed_values.match(validated_value):
                raise ParameterError('Values is not matching pattern %s' % allowed_values.pattern)
            
            
        return validated_value

    def execute(self):
        raise NotImplemented
    
    
    
class ActionsRunner(threading.Thread):
    def __init__(self, actions_list, finished_cb=None, cb_thread_safe=True):
        threading.Thread.__init__(self,name="ActionsRunner")
        self.finished_cb=finished_cb
        self.cb_thread_safe=cb_thread_safe
        self.actions=actions_list
        self.finished_ok=[]
        self.had_error=[]
        self.setDaemon(True)
        
    def run(self):
        for a in self.actions:
            action=get_action(a)
            if action:
                try:
                    action.execute()
                except Exception,e:
                    log.exception('Action %s has error %s', a, e)
                    self.had_error.append((a, str(e)))
                else:
                    log.debug('Action %s executed ok', a)
                    self.finished_ok.append(a)
            else:
                log.error("Action %s not defined", a)
                self.had_error.append((a, 'Action not defined'))
                
        if self.finished_cb:
            if self.cb_thread_safe:
                self.finished_cb(self.finished_ok, self.had_error)
            else:
                def _wrapper():
                    self.finished_cb(self.finished_ok, self.had_error)
                    return False
                GObject.idle_add(_wrapper)
        
        
def main():
    pass
    
    
if __name__=='__main__':
    main()