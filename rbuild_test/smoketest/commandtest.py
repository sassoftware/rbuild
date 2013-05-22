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
import sys


from testutils import mock
from rbuild_test import rbuildhelp
from conary.lib import cfg

from rbuild.internal import pluginloader
from rbuild.internal import main

class CommandTest(rbuildhelp.RbuildHelper):

    def testBasic(self):
        # can we get to build packages?
        pluginloader.getPlugins([], self.rbuildCfg.pluginDirs)
        os.mkdir(self.rootDir + '/etc')
        self.rbuildCfg.store(open(self.rootDir + '/etc/rbuildrc', 'w'))
        self.checkRbuild('build packages', 
                 'rbuild_plugins.buildpackages.BuildPackagesCommand.runCommand',
                 [None, None, {}, ['build', 'packages']])

    def testSysArgv(self):
        argv = [ 'rbuild', 'update', ]
        self.mock(main.RbuildMain, 'main', mock.MockObject())
        self.mock(sys, 'argv', argv)
        main.main()
        mainArgs = main.RbuildMain.main._mock.popCall()[0][0]
        assert mainArgs == argv
        self.unmock()


