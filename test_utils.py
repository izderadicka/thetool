'''
Created on Nov 22, 2012

@author: ivan
'''
import unittest
from utils import *

class Test(unittest.TestCase):


    def testIp(self):
        num=0x01020304
        ip=ip4_to_str(num, rev=True)
        self.assertEqual(ip, '1.2.3.4')
        ip=ip4_to_str(num)
        self.assertEqual(ip, '4.3.2.1')
        num2=ip4_to_number(ip)
        self.assertEqual(num2, num)
        num3=ip4_to_number('1.2.3.4', rev=True)
        self.assertEqual(num3, num)
        
    def testMarchIp(self):
        mask='255.255.254.0'
        ip1='192.168.224.123'
        ip2='192.168.225.03'
        self.assertTrue(match_ip(ip1, ip2, mask))
        self.assertFalse(match_ip(ip1, '192.168.226.123', mask))

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.test']
    unittest.main()