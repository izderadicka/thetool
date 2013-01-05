'''
Created on Dec 27, 2012

@author: ivan
'''

import subprocess

class ExecuteCommand(Action):    #@UndefinedVariable
    PARAMS_DEFINITION=(('commands', True, basestring),
                       ('wait', False, bool)
                       )
    DESCRIPTION= 'Executes commands in child shell process - either do not wait for result (wait false), or can wait for commands to complete'
    def execute(self):
        cmd=self.get_param('commands')
        proc=subprocess.Popen(cmd, shell=True);
        if  self.get_param('wait'):
            ret_code=proc.wait()
            if ret_code!=0:
                raise Exception("Process terminates with ret_code %d"% ret_code)
    
register_type(ExecuteCommand, 'Executes Shell Commands') #@UndefinedVariable