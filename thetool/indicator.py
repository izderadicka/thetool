'''
Created on Jun 1, 2013

@author: ivan
'''
from gi.repository import Gtk
from gi.repository import AppIndicator3 as appindicator
import os

_curr_dir=os.path.split(__file__)[0]
def menuitem_response(w, buf):
    print buf

if __name__ == "__main__":
    
    icon_factory=Gtk.IconFactory()
    icon_source=Gtk.IconSource()
    f=os.path.join(_curr_dir, 'pics', 'tools.png')
    if not os.path.exists(f):
        raise Exception('Image %s missing'%f)
    icon_source.set_filename(f)
    icon_source.set_size_wildcarded(True)
    icon_set=Gtk.IconSet()
    icon_set.add_source(icon_source)
    icon_factory.add('myapp-icon', icon_set)
    icon_factory.add_default()
    
    ind = appindicator.Indicator.new (
                          "example-simple-client",
                          "emblem-generic",
                          appindicator.IndicatorCategory.APPLICATION_STATUS)
    ind.set_status (appindicator.IndicatorStatus.ACTIVE)
    ind.set_attention_icon ("indicator-messages-new")
    ind.set_label("test", "test")
    
    # create a menu
    menu = Gtk.Menu()

    # create some 
    for i in range(3):
        buf = "Test-undermenu - %d" % i
        
        menu_items = Gtk.MenuItem(buf)
        
        menu.append(menu_items)
        
        # this is where you would connect your menu item up with a function:
        
        # menu_items.connect("activate", menuitem_response, buf)
        
        # show the items
        menu_items.show()
    
    ind.set_menu(menu)
    
    Gtk.main()
