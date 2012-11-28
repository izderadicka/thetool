'''
Created on Nov 14, 2012

@author: ivan
'''
import logging
logging.basicConfig(level=logging.DEBUG)
import unittest
from thetool.gdbus import *
from thetool.netmanager import NetworkManagerMonitor
from thetool.mplayer2 import get_active_player


class TestDBus(unittest.TestCase):
    def setUp(self):
        pass
        
    def testNMVersion(self):
        self.nm=NetworkManagerMonitor()
        version=self.nm.Version
        print version
        self.assertTrue(len(version)>0)
        
    def testNMActiveConnections(self):
        self.nm=NetworkManagerMonitor()
        conn= self.nm.get_default_connection_info()
        print conn
        
    def testListBus(self):
        names = list_names('session')
        print names
        self.assertTrue(names)
        
    def testPlayer(self):
        p=get_active_player()
        
    