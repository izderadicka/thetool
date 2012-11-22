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
log=logging.getLogger('TheTool - Actions')

ACTIONS_FILE=os.path.expanduser('~/.config/thetool/actions.json')
_known_actions_types={}
_actions={}

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
    
def add_action(action):
    _actions[action.name]=action
    save()
    
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
    ACTION_UI_FILE=None   # subclasses should define ui file for action (created in glade) 
    PARAMS_DEFINITION= None#('name' ,  True/False <Mandatory> -,  str <type - python type), ...)
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
            if value.lower() in no:
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
                raise ParameterError('Value not in allowed values %s' % allowed_values)
            
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
    
    
    
class ChangeProxyAction(Action):    
    PARAMS_DEFINITION=(('host', True, basestring),
                       ('port', True, int),
                       ('protocols', False, list),
                       ('ignore_hosts', False, basestring)
                       )
    
    def execute(self):
        print 'Bude'
        
register_type(ChangeProxyAction, 'Change Proxy')        
        
def main():
    oracle_proxy=ChangeProxyAction("Oracle proxy")
    oracle_proxy.set_param('host', 'my.dom.com')
    oracle_proxy.set_param('port', '10')
    s=dumps({"my_action":oracle_proxy})
    print oracle_proxy, s
    o=loads(s)
    print o
    
    
if __name__=='__main__':
    main()