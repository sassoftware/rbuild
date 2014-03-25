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


from testutils import mock

from rbuild_test import rbuildhelp


class ListPlatformsTest(rbuildhelp.RbuildHelper):
    def testCommandParsing(self):
        handle = self.getRbuildHandle()
        handle.List.registerCommands()
        handle.List.initialize()
        handle.Platforms.initialize()
        cmd = handle.Commands.getCommandClass('list')()

        mock.mockMethod(handle.Platforms.list)
        _platform = mock.MockObject()
        _platform._mock.enable('enabled')
        _platform._mock.set(enabled='true')
        handle.Platforms.list._mock.setReturn([_platform])

        cmd.runCommand(handle, {}, ['rbuild', 'list', 'platforms'])
        handle.Platforms.list._mock.assertCalled()

    def testCommand(self):
        self.getRbuildHandle()
        self.checkRbuild(
            'list platforms',
            'rbuild_plugins.platforms.ListPlatformsCommand.runCommand',
            [None, None, {}, ['list', 'platforms']],
            )


class PlatformsPluginTest(rbuildhelp.RbuildHelper):
    def testList(self):
        handle = self.getRbuildHandle()

        mock.mockMethod(handle.facade.rbuilder.getPlatforms)

        _platform1 = mock.MockObject()
        _platform1._mock.set(hidden='false')

        _platform2 = mock.MockObject()
        _platform2._mock.set(hidden='true')

        handle.facade.rbuilder.getPlatforms._mock.setReturn(
            [_platform1, _platform2])

        rv = handle.Platforms.list()
        self.assertEqual(rv, [_platform1])

        rv = handle.Platforms.list(hidden=True)
        self.assertEqual(rv, [_platform1, _platform2])
