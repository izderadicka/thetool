#!/usr/bin/env python
'''
Created on Nov 24, 2012

@author: ivan
'''

from distutils.core import setup
from distutils.command.install import install
import os
import shutil

class my_install(install):
    def run(self):
        install.run(self)
        self.post_install()
    def post_install(self):
        print "Running post-install"
        shutil.copy('thetool/eu.zderadicka.thetool.gschema.xml', '/usr/share/glib-2.0/schemas')
        os.chmod('/usr/share/glib-2.0/schemas/eu.zderadicka.thetool.gschema.xml', 0O644) #assure it's
        ret=os.system(' glib-compile-schemas /usr/share/glib-2.0/schemas/')
        if ret!=0:
            raise ('Compilation of schemas failed')

from thetool.thetool import __version__ as version
setup(name='thetool',
      version=version,
      author='Ivan',
      author_email='ivan.zderadicka@g=gmail.com',
      url=['http://zderadicka.eu/projects/python/thetool-quick-actions-for-desktop/'],
      packages=['thetool'],
      package_data={'thetool':['actions/*.py', 'pics/*', 'ui/*', '*.gschema.xml']},
      scripts=['the-tool'],
      requires=['gi(>=3.2)'],
      cmdclass={'install': my_install},
      )