'''
Created on Nov 19, 2012

@author: ivan
'''
import unittest
import re
import actions

class DummyAction(actions.Action):
    PARAMS_DEFINITION=(('string1', True, basestring),
                       ('string2', False, str),
                       ('string3', True, unicode),
                       ('int1', True, int),
                       ('list1', True, list),
                       ('bool1', False, bool),
                       ('restricted1', True, str, ['opt1', 'opt2', 'opt3']),
                       ('restricted2', True, list, ['opt1', 'opt2', 'opt3']),
                       ('float1', True, float),
                       ('dict1', True, dict),
                       ('reg1', True, str, re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'))
                       )

class Test(unittest.TestCase):


    def setUp(self):
        self.a=DummyAction('My Dummy')

    def tearDown(self):
        pass


    def testCorrect(self):
        vals=(('string1', "True", basestring),
               ('string2', None, str),
               ('string3', u"Uni", unicode),
               ('int1', '5', int),
               ('list1', 'ano, ne', list),
               ('bool1', "False", bool),
               ('restricted1', 'opt3', str),
               ('restricted2', 'opt1, opt3', list),
               ('float1', '1.1', float),
               ('dict1', "a:b, aano:nne", dict),
               ('reg1', '11.22.33.44', str)
               )
        
        for name,val,type in vals:
            self.a.set_param(name, val)
            stored=self.a.get_param(name)
            if type not in (list,dict,bool, basestring):
                self.assertEqual(type(val) if val!=None else None, stored)
            self.assertEqual(val, self.a.get_param_as_str(name))
        self.assertEqual(self.a.get_param('list1'), ['ano','ne'])
        
    def testIncorrect(self):
        vals=(('string1', None, basestring),
               
               ('string3', "", unicode),
               ('int1', 'ab3', int),
               ('list1', ',', list),
               ('bool1', "neco", bool),
               ('restricted1', 'jine', str),
               ('restricted2', 'opt1, nesmy', list),
               ('float1', 'x.a', float),
               ('dict1', "a:b, aano:", dict),
               ('reg1', '.22.33.44', str)
               )
        
        for name,val,type in vals:
            try:
                self.a.set_param(name, val)
                print "not failed value is %s" % self.a.get_param(name)
                self.fail('Should raise error for %s'% name)
                
            except actions.ParameterError:
                pass
            
    def testIncorrect2(self):
        vals=(
               ('restricted1', 'jine', str),
               
               )
        
        for name,val,type in vals:
            try:
                self.a.set_param(name, val)
                print "not failed value is %s" % self.a.get_param(name)
                self.fail('Should raise error for %s'% name)
                
            except actions.ParameterError:
                pass
if __name__ == "__main__":
    import sys;sys.argv = ['', 'Test.testIncorrect2']
    unittest.main()