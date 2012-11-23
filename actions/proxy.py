class ChangeProxyAction(Action):    # @UndefinedVariable
    PARAMS_DEFINITION=(('host', True, basestring),
                       ('port', True, int),
                       ('protocols', False, list, ('http', 'https', 'ftp', 'socks')),
                       ('ignore_hosts', False, list),
                       )
    DESCRIPTION= "Sets manual proxy for current user (via GSettings). "
    def execute(self):
        print 'Bude'
        
register_type(ChangeProxyAction, 'Set Manual Proxy')   #@UndefinedVariable

class SetProxyModeAction(Action):    #@UndefinedVariable
    PARAMS_DEFINITION=(('mode', True, basestring, ("none", "manual", "auto")),
                       
                       )
    DESCRIPTION= 'Select the proxy configuration mode. Supported values are "none", "manual", "auto". (via GSettings). '
    def execute(self):
        print 'Bude'
        
register_type(SetProxyModeAction, 'Select Proxy Mode') #@UndefinedVariable