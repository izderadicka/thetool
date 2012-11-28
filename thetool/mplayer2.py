'''
Created on Nov 27, 2012

@author: ivan
'''
import logging
log=logging.getLogger('mplayer2')
from gdbus import DBusProxyWrapper, list_names

MPRIS_NAME='org.mpris.MediaPlayer2'

def pause_all():
    names=list_names('session')
    for name in names:
        if name.startswith(MPRIS_NAME):
            player=Player(name, sync_props=True)
            status=player.get_property('PlaybackStatus')
            if status=='Playing':
                player.Pause()


def get_active_player(listening=False):
    active=[]
    names=list_names('session')
    for name in names:
        if name.startswith(MPRIS_NAME):
            player=Player(name, receive_signals=listening, sync_props=True)
            status=player.get_property('PlaybackStatus')
            if status=='Playing':
                active.append(player)
    if len(active)> 1:
        log.warn('Have %d players active - dont know which to choose', len(active))
        #TODO: Resolve when many player are running - have favorite one?
        return None
    elif len(active)==1:
        return active[0]
    else:
        return None
    
class PlayerMonitor(object):
    def __init__(self, on_stop_cb):
        self.on_stop_cb=on_stop_cb
        self.player=get_active_player(listening=True)
        if self.player:
            log.debug('Active player is %s', self.player.bus_name)
            self.player.add_listener('PropertiesChanged', self.on_properties_changed)
        else:
            log.debug("There is no active player")
        
    def is_active(self):
        return self.player is not None
    
    @property
    def name(self):
        return self.player.bus_name[len(MPRIS_NAME)+1:] if self.player else None
    
    def close(self):
        if self.player:
            self.player.disconnect()
            self.player.remove_listener('PropertiesChanged', self.on_properties_changed)
            
            
    def on_properties_changed(self, itf, props, invalidated):
        log.debug('Player properties changed %s', props)
        if props.has_key('PlaybackStatus') and props['PlaybackStatus']=='Stopped':
            log.debug("Player stopped")
            if self.on_stop_cb:
                self.on_stop_cb()
            
        
    
    
 
class Player(DBusProxyWrapper):  
    def __init__(self, bus_name, sync_props=False, receive_signals=False):  
        DBusProxyWrapper.__init__(self, 'session', bus_name, '/org/mpris/MediaPlayer2', 
                         'org.mpris.MediaPlayer2.Player', sync_props, receive_signals)

if __name__=='__main__':
    from gi.repository import GObject
    logging.basicConfig(level=logging.DEBUG)
    main=GObject.MainLoop()
    def _stop():
        main.quit()
    p=PlayerMonitor(_stop)
    
    if p.is_active():
        main.run()
        
    p.close()