from gi.repository import Gio, GLib #@UnresolvedImport

class ChangeProxyAction(Action):    # @UndefinedVariable
    PARAMS_DEFINITION=(('host', True, basestring),
                       ('port', True, int),
                       ('protocols', False, list, ('http', 'https', 'ftp', 'socks')),
                       ('ignore_hosts', False, list),
                       )
    DESCRIPTION= "Sets manual proxy for current user (via GSettings). If protocols are not given, sets proxy for http, https and ftp"
    def execute(self):
        settings = Gio.Settings('org.gnome.system.proxy')
        protocols=self.get_param('protocols')
        all_protocols=('http', 'https', 'ftp', 'socks')
        for p in all_protocols:
            if p in ('http', 'https', 'ftp') and (not protocols or p in protocols ) or \
               p == 'socks' and p in protocols:
                psettings=settings.get_child(p)
                psettings.set_string('host',self.get_param('host'))
                psettings.set_int('port',self.get_param('port'))
            else:
                psettings=settings.get_child(p)
                psettings.set_string('host','')
                psettings.set_int('port',0)
        ignore=self.get_param('ignore_hosts')
        if  ignore:
            settings.set_value('ignore-hosts', GLib.Variant('as', self.get_param('ignore_hosts')))
        settings.set_string('mode', 'manual')
        
        
register_type(ChangeProxyAction, 'Set Manual Proxy')   #@UndefinedVariable

class SetProxyModeAction(Action):    #@UndefinedVariable
    PARAMS_DEFINITION=(('mode', True, basestring, ("none", "auto")),
                       ('autoconfig-url', False, basestring)
                       )
    DESCRIPTION= 'Select the proxy configuration mode. Supported values are "none",  "auto" (for "manual see other action, when you set also proxy details). (via GSettings).'
    def execute(self):
        settings = Gio.Settings('org.gnome.system.proxy')
        mode=self.get_param('mode')
        settings.set_string('mode', mode)
        if mode=='auto':
            settings.set_string('autoconfig-url', self.get_param('autoconfig-url'))
            
        
register_type(SetProxyModeAction, 'Select Proxy Mode') #@UndefinedVariable