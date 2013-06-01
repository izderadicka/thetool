'''
Created on Jun 1, 2013

@author: ivan
'''
from gi.repository import Gtk
from gi.repository import AppIndicator3 as appindicator


def menuitem_response(w, buf):
  print buf

if __name__ == "__main__":
  ind = appindicator.Indicator.new (
                        "example-simple-client",
                        "indicator-messages",
                        appindicator.IndicatorCategory.APPLICATION_STATUS)
  ind.set_status (appindicator.IndicatorStatus.ACTIVE)
  ind.set_attention_icon ("indicator-messages-new")

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
