TheTool is small tool enabling one to quickly set do some tasks (task that related to everyday usage) in Linux desktop. This tool is rebuild of older toshtool utility, which I used for years, now completely rewritten with GTK3 framework and python (using GObject Introspection in python). The tool sits in the tray and actions are just a click away.

Recently this enables this tasks:

    Immediately turn off display
    Schedule computer suspend (shut down or hibernate) in given interval in very quick way.  Also possibility to cancel planned suspend by just one click.
		one click proxy switching (as I connect to different networks in is bit annoying)
    automatic detection of network and then enabling right proxy – based some advanced configuration
    
Since I’m using my computer to listen music , audio books at evening I want to sent some time-out, so computer suspends after I fall asleep.  I missed some easy tool to enable this in few clicks, so I built this one.


I plan also to add more features:

    Power off when a  player (with DBus Interface enabled)  finish playing
    one click disabling of screensaver ( not all video player have support for disabling screensaver)
    any other idea for quick task that need to be accessible very quickly

Will see what plans I can realize.

Version History:

0.1 - Initial version 
0.2 - With Network changed detetection and proxies switching