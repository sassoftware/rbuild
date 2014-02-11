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
from testutils import mock

from rbuild_test import rbuildhelp


class CancelTest(rbuildhelp.RbuildHelper):
    def testCancelCommandParsing(self):
        handle = self.getRbuildHandle(mock.MockObject())
        handle.Cancel.registerCommands()
        handle.Cancel.initialize()
        cmd = handle.Commands.getCommandClass('cancel')()

        mock.mockMethod(handle.Cancel.cancelImages)
        cmd.runCommand(handle, {}, ['rbuild', 'cancel', 'images'])
        handle.Cancel.cancelImages._mock.assertCalled([])
        cmd.runCommand(handle, {}, ['rbuild', 'cancel', 'images', 'foo'])
        handle.Cancel.cancelImages._mock.assertCalled(['foo'])
        cmd.runCommand(
            handle, {}, ['rbuild', 'cancel', 'images', 'foo', 'bar'])
        handle.Cancel.cancelImages._mock.assertCalled(['foo', 'bar'])

    def test_cancelImage(self):
        handle = self.getRbuildHandle(mock.MockObject())
        handle.Cancel.registerCommands()
        handle.Cancel.initialize()

        mock.mockMethod(handle.Cancel._promptUser)
        mock.mockMethod(handle.Cancel._getCancelBuildJob)
        _job = mock.MockObject()
        _job._mock.set(status_code='200')
        _bad_job = mock.MockObject()
        _bad_job._mock.set(status_code='500')

        handle.Cancel._promptUser._mock.setReturn(True, 'image1')
        handle.Cancel._promptUser._mock.setReturn(True, 'image2')
        handle.Cancel._promptUser._mock.setReturn(False, 'image3')
        handle.Cancel._getCancelBuildJob._mock.setReturn(_job, 'image1')
        handle.Cancel._getCancelBuildJob._mock.setReturn(_bad_job, 'image2')

        handle.Cancel._cancelImage('image3')
        handle.Cancel._promptUser._mock.assertCalled('image3')
        handle.Cancel._getCancelBuildJob._mock.assertNotCalled()

        handle.Cancel._cancelImage(['image1'])
        handle.Cancel._promptUser._mock.assertCalled('image1')
        handle.Cancel._getCancelBuildJob._mock.assertCalled('image1')

        self.assertRaises(
            errors.PluginError,
            handle.Cancel._cancelImage,
            ['image1', 'image2'],
            )
        handle.Cancel._promptUser._mock.assertCalled('image1')
        handle.Cancel._getCancelBuildJob._mock.assertCalled('image1')
