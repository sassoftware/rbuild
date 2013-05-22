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

class PublishTest(rbuildhelp.RbuildHelper):
    def testCommandParsing(self):
        handle = self.getRbuildHandle()
        handle.Publish.registerCommands()
        handle.Publish.initialize()
        cmd = handle.Commands.getCommandClass('publish')()
        mock.mockMethod(handle.Publish.getReleaseId, 1)
        mock.mockMethod(handle.Publish.publishRelease, None)

        cmd.runCommand(handle, {}, ['rbuild', 'publish'])
        handle.Publish.getReleaseId._mock.assertCalled()
        handle.Publish.publishRelease._mock.assertCalled(1, 1)

        cmd.runCommand(handle, {'no-mirror' : True}, ['rbuild', 'publish'])
        handle.Publish.getReleaseId._mock.assertCalled()
        handle.Publish.publishRelease._mock.assertCalled(1, False)

        handle.Publish.getReleaseId._mock.setDefaultReturn(None)
        self.assertRaises(errors.PluginError, cmd.runCommand, handle, {}, ['rbuild', 'publish'])
        handle.Publish.publishRelease._mock.assertNotCalled()

        handle.Publish.getReleaseId._mock.setDefaultReturn(0)
        self.assertRaises(errors.PluginError, cmd.runCommand, handle, {}, ['rbuild', 'publish'])
        handle.Publish.publishRelease._mock.assertNotCalled()

        cmd.runCommand(handle, {}, ['rbuild', 'publish', '1', '2'])
        handle.Publish.publishRelease._mock.assertCalled(1, True)
        handle.Publish.publishRelease._mock.assertCalled(2, True)

    def testGetReleaseId(self):
        handle = self.getRbuildHandle()
        handle.productStore = mock.MockObject()
        handle.productStore.getStageReleaseId._mock.setDefaultReturn(42)

        rc = handle.Publish.getReleaseId()
        handle.productStore.getStageReleaseId._mock.assertCalled()
        assert(rc==42)

    def testPublishRelease(self):
        handle = self.getRbuildHandle()
        mock.mockMethod(handle.facade.rbuilder.publishRelease, None)
        rc = handle.Publish.publishRelease(1, 1)
        handle.facade.rbuilder.publishRelease._mock.assertCalled(1, 1)

    def testCommand(self):
        handle = self.getRbuildHandle()
        self.checkRbuild('publish',
            'rbuild_plugins.publish.PublishCommand.runCommand',
            [None, None, {},
            ['rbuild', 'publish']])

