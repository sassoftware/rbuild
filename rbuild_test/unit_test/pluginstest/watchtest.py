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



from rbuild_test import rbuildhelp
from testutils import mock

class WatchTest(rbuildhelp.RbuildHelper):
    def testWatchCommandParsing(self):
        handle = self.getRbuildHandle(mock.MockObject())
        handle.Watch.registerCommands()
        handle.Watch.initialize()
        cmd = handle.Commands.getCommandClass('watch')()
        mock.mockMethod(handle.Build.watchJob)
        mock.mockMethod(handle.facade.rbuilder.watchImages)
        handle.productStore.getPackageJobId._mock.setReturn(10)
        handle.productStore.getGroupJobId._mock.setReturn(20)
        handle.productStore.getImageJobIds._mock.setReturn([30])
        cmd.runCommand(handle, {}, ['rbuild', 'watch', 'packages'])
        handle.Build.watchJob._mock.assertCalled(10)
        cmd.runCommand(handle, {}, ['rbuild', 'watch', 'groups'])
        handle.Build.watchJob._mock.assertCalled(20)
        cmd.runCommand(handle, {}, ['rbuild', 'watch', 'images'])
        handle.facade.rbuilder.watchImages._mock.assertCalled([30])
        cmd.runCommand(handle, {}, ['rbuild', 'watch', 'job', '20'])
        handle.Build.watchJob._mock.assertCalled('20')
