'''
Created on Jun 1, 2013

@author: ivan
'''
import logging
import os
log=logging.getLogger('Tray')
from gi.repository import Gtk, GdkPixbuf #@UnresolvedImport

_curr_dir=os.path.split(__file__)[0]

try:
    from gi.repository import AppIndicator3  # @UnresolvedImport
    HAS_INDICATOR=True
except:
    HAS_INDICATOR=False
    
    
def create(menu, activate_cb, force_tray=False):
    if HAS_INDICATOR and not force_tray:
        return Indicator(menu)
    else:
        return Tray(menu, activate_cb)
    
class Indicator(object):    
    def __init__(self, menu):
        self.ind = AppIndicator3.Indicator.new (
                          "thetool",
                          "",
                          AppIndicator3.IndicatorCategory.APPLICATION_STATUS)
        self.ind.set_status (AppIndicator3.IndicatorStatus.ACTIVE)
        self.ind.set_icon(os.path.join(_curr_dir, 'pics', 'tools.png'))
        self.ind.set_attention_icon (os.path.join(_curr_dir, 'pics', 'tools-active.png'))
        self.ind.set_menu(menu)
        

    def set_tooltip_text(self, txt, **kwargs):
        if kwargs.get('time'):
            t=str(kwargs['time'])
            self.ind.set_label(t,t)
        else:
            self.ind.set_label('', '')
    
    def set_attention(self, attention):
        if attention:
            self.ind.set_status (AppIndicator3.IndicatorStatus.ATTENTION)
        else:
            self.ind.set_status (AppIndicator3.IndicatorStatus.ACTIVE)
        

class Tray(object):
    def __init__(self, menu, activate_cb=None):
        self.tray_icon=Gtk.StatusIcon()
        self.tray_icon.set_visible(True)
        self.tray_icon.set_title("TheTool")
        self.tray_icon.connect('popup-menu', self._show_menu)
        self.tray_icon.connect('activate', self._activate)
        self.icon_normal=GdkPixbuf.Pixbuf.new_from_file(os.path.join(_curr_dir, 'pics', 'tools.png'))
        self.icon_power_off=GdkPixbuf.Pixbuf.new_from_file(os.path.join(_curr_dir, 'pics', 'tools-active.png'))
        self.menu=menu
        self.activate_cb=activate_cb
        
    
    def _show_menu(self, tray_icon, button, activate_time, user_data=None):  
        def pos(menu, icon): 
            p= Gtk.StatusIcon.position_menu(menu, icon)
            return p
        log.debug( 'Menu button=%s, time=%s', button, activate_time)
        self.menu.popup(None, None, pos, tray_icon, button, activate_time )
        
    def _activate(self, tray_icon, user_data=None): 
        if self.activate_cb:
            self.activate_cb()
    
    def set_tooltip_text(self, txt, **kwargs):
        self.tray_icon.set_tooltip_text(txt)
        
    def _set_icon(self):
        width,height=22,22
        icon=self.current_icon.scale_simple(width,height, GdkPixbuf.InterpType.NEAREST)
        self.tray_icon.set_from_pixbuf(icon)
        
    def set_attention(self, attention):
        if attention:
            self.current_icon=self.icon_power_off
        else:
            self.current_icon=self.icon_normal
        self._set_icon()
            
    
