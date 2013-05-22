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

from rbuild_test import rbuildhelp

from conary.lib import util

from rbuild import handle, rbuildcfg

class PluginTest(rbuildhelp.RbuildHelper):
    def myHook(self, *args, **kw):
        print 'My hook!'

    def testBasic(self):
        # can we access plugins from the handle?
        configPath = self.cfg.root + '/etc/rbuildrc'
        util.mkdirChain(os.path.dirname(configPath))
        rbuildCfg = self.rbuildCfg
        self.rbuildCfg.store(open(configPath, 'w'))
        self.mock(rbuildcfg, 'RbuildConfiguration',
            lambda *args, **kw: rbuildCfg)
        rbuildHandle = handle.RbuildHandle()
        assert(rbuildHandle.Build)
        # can we install + use a hook?
        rbuildHandle.installPrehook(rbuildHandle.Config.displayConfig,
                                    self.myHook)
        _, txt  = self.captureOutput(rbuildHandle.Config.displayConfig, 
                                     rbuildHandle)
        assert(txt.split('\n')[0] == 'My hook!')


