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



from rbuild import errors
from rbuild_test import rbuildhelp
from testutils import mock

class BuildPlatformTest(rbuildhelp.RbuildHelper):
    def testCommandParsing(self):
        handle = self.getRbuildHandle()
        handle.Build.registerCommands()
        handle.Build.initialize()
        handle.BuildPlatform.initialize()
        cmd = handle.Commands.getCommandClass('build')()
        mock.mockMethod(handle.BuildPlatform.buildPlatform)

        err = self.assertRaises(errors.PluginError, cmd.runCommand, handle, {},
                                ['rbuild', 'build', 'platform'])
        self.assertIn('rbuild init', str(err))

        mock.mock(handle, 'productStore')

        cmd.runCommand(handle, {}, ['rbuild', 'build', 'platform'])
        handle.BuildPlatform.buildPlatform._mock.assertCalled()

    def testBuildPlatform(self):
        handle = self.getRbuildHandle(mock.MockObject())
        mock.mockMethod(handle.facade.conary._getConaryClient)
        client = handle.facade.conary._getConaryClient()
        handle.BuildPlatform.buildPlatform()
        handle.product.savePlatformToRepository._mock.assertCalled(client)

