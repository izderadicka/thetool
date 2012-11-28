TheTool is a small tool enabling one to quickly do some tasks (tasks that relate to everyday usage) 
in Linux desktop. This tool is rebuild of older toshtool utility, which I used for years, 
now completely rewritten with GTK3 framework and python (using GObject Introspection in python). 
The tool sits in the tray and actions are just a click away.

Recently it enables these tasks:

    * Immediately turn off display
    * Schedule computer suspend (shut down or hibernate) in given interval in very quick way.  Also 
    possibility to cancel planned suspend by just one click.
    * Automatic detection of network (based on name and subnet for wired connection) and 
    then running some actions 
    * Flexible system of actions - new actions can be easily written as plugins
    * Currently actions include setting and resetting proxy
    * Any action can be set for quick access via tray icon menu
    
Since I’m using my computer to listen music , audio books at evening I want to set some time-out, 
so computer suspends after I fall asleep.  I missed some easy tool to enable this in few clicks, 
so I built this one. Another problem was connecting with notebook to different networks, some require 
proxy some not - automatic proxy configuration do not work well (a bit for browser, but not for other
programs - shell, pidgin ...) so this was another function that I added to the tool.

I plan also to add more features:

    * More actions - change any setting via GSettings, call any DBUS method, launch programs, 
    disable/enabe ports
    * Power off when a  player (with DBus Interface enabled)  finishes playing
    * One click disabling of screensaver ( not all video player have support for disabling 
    screensaver)
    * Any other idea for quick task that need to be accessible very quickly

Will see what plans I can realize.

TheTool is licensed under GPL v3 - http://www.gnu.org/licenses/gpl.html

To install on your system run: sudo ./setup.py install and run the-tool command
 
If you want to observe it first or develop, you can run from source - but you must first 
compile GSettings schema in thetool directory:
glib-compile-schemas --strict thetool

./the-tool

TheTool web http://zderadicka.eu/projects/python/thetool-quick-actions-for-desktop/

Version History:

0.1 - Initial version 
0.2 - With network changed detetection, proxies switching and flexible action system