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

from rbuild import errors


class ShowGroupsTest(rbuildhelp.RbuildHelper):
    def testShowGroupsCommandParsing(self):
        handle = self.getRbuildHandle(mock.MockObject())
        handle.Show.registerCommands()
        handle.ShowGroups.registerCommands()
        handle.ShowGroups.initialize()
        cmd = handle.Commands.getCommandClass('show')()
        mock.mockMethod(handle.ShowGroups.showGroupStatus)
        cmd.runCommand(handle, {}, ['rbuild', 'show', 'groups'])
        handle.ShowGroups.showGroupStatus._mock.assertCalled()

    def testShowGroupStatus(self):
        handle = self.getRbuildHandle(mock.MockObject())
        handle.productStore.getGroupJobId._mock.setReturn(10)
        mock.mockMethod(handle.Show.showJobStatus)
        assert(handle.ShowGroups.showGroupStatus() == 10)
        handle.Show.showJobStatus._mock.assertCalled(10)
        handle.productStore.getGroupJobId._mock.setReturn(None)
        err = self.assertRaises(errors.PluginError, 
                                handle.ShowGroups.showGroupStatus)
        assert(str(err) == 'No groups have been built in this environment')


