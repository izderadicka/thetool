'''
Created on Nov 14, 2012

@author: ivan
'''
import logging
logging.basicConfig(level=logging.DEBUG)
import unittest
from gdbus import *


class TestDBus(unittest.TestCase):
    def setUp(self):
        self.nm=nm=NetworkManager()
    def testNMVersion(self):
        
        version=self.nm.Version
        print version
        self.assertTrue(len(version)>0)
        
    def testNMActiveConnections(self):
        print self.nm.get_default_connection_info()
        
    