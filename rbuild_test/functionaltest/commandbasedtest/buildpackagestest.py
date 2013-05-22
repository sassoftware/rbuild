#!/usr/bin/python
#
# Copyright (c) SAS Institute Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#



import os
import re

from rbuild_test import rbuildhelp
from conary_test import recipes

from conary.deps import deps
import platform
machineMacros = { 'machineType' : {'i686': 'x86',
                                   'x86_64': 'x86_64'}[platform.machine()],
                  'machineFlavor' : {'i686' : 'x86(~i486,~i586,~i686)',
                                     'x86_64' : 'x86_64'}[platform.machine()] }

class BuildPackagesTest(rbuildhelp.CommandTest):
    def testBuildPackages3(self):
        self.addCollection('group-dist', ['simple:run'])
        self.initProductDirectory('foo')
        os.chdir('foo/devel')
        txt = self.runCommand('build packages --recurse blah', exitCode=1)
        assert(txt == 'error: the following packages were not found: blah\n')
        txt = self.runCommand('build packages --recurse', exitCode=1)
        assert(txt == 'error: no packages are currently'
                      ' being edited - nothing to build\n')


groupRecipe = """
class GroupDist(GroupRecipe):
    name = 'group-dist'
    version = '1.0'

    def setup(r):
        r.add('simple')
        #r.add('simple2', flavor='~simple2.flag')
        r.add('simple3')
        r.add('unrelated')
"""

