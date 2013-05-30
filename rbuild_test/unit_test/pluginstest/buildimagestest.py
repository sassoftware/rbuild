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

class BuildImagesTest(rbuildhelp.RbuildHelper):
    def testCommandParsing(self):
        handle = self.getRbuildHandle()
        handle.Build.registerCommands()
        handle.Build.initialize()
        handle.BuildImages.initialize()
        cmd = handle.Commands.getCommandClass('build')()
        mock.mockMethod(handle.BuildImages.buildImages, 1)
        mock.mockMethod(handle.Build.watchJob)
        mock.mockMethod(handle.facade.rmake.isJobBuilt, True)
        mock.mockMethod(handle.BuildImages.printImageUrlsForJob)
        handle.productStore = mock.MockObject()
        handle.product = mock.MockObject()
        cmd.runCommand(handle, {}, ['rbuild', 'build', 'images'])
        handle.BuildImages.buildImages._mock.assertCalled(None)
        handle.Build.watchJob._mock.assertCalled(1)
        handle.facade.rmake.isJobBuilt._mock.assertCalled(1)

        cmd.runCommand(handle, {}, ['rbuild', 'build', 'images', 'image 1', 'image 2'])
        handle.BuildImages.buildImages._mock.assertCalled(['image 1', 'image 2'])

        cmd.runCommand(handle, {}, ['rbuild', 'build', 'images'])

        cmd.runCommand(handle, {'no-watch':True},
            ['rbuild', 'build', 'images'])

        handle.facade.rmake.isJobBuilt._mock.setDefaultReturn(False)
        self.assertRaises(errors.PluginError,
            cmd.runCommand, handle, {}, ['rbuild', 'build', 'images'])

    def testBuildAllImages(self):
        handle = self.getRbuildHandle()
        handle.productStore = mock.MockObject()
        handle.product = mock.MockObject()
        mock.mockMethod(handle.facade.rmake.createImagesJobForStage,
                        'job')
        mock.mockMethod(handle.facade.rmake.buildJob, 31)
        mock.mockMethod(handle.Build.warnIfOldProductDefinition)
        rc = handle.BuildImages.buildImages()
        handle.facade.rmake.createImagesJobForStage._mock.assertCalled(None)
        handle.facade.rmake.buildJob._mock.assertCalled('job')
        handle.productStore.setImageJobId._mock.assertCalled(31)
        assert(rc == 31)
        handle.Build.warnIfOldProductDefinition._mock.assertCalled(
            'building images')

    def testCommand(self):
        handle = self.getRbuildHandle()
        self.checkRbuild('build images --no-watch',
            'rbuild_plugins.buildimages.BuildImagesCommand.runCommand',
            [None, None, {'no-watch' : True,},
            ['build', 'images']])
        self.checkRbuild('build images --no-watch "image 1"',
            'rbuild_plugins.buildimages.BuildImagesCommand.runCommand',
            [None, None, {'no-watch' : True},
            ['build', 'images', 'image 1']])

    def testPrintImageUrlsForJob(self):
        handle = self.getRbuildHandle()
        mock.mockMethod(handle.facade.rmake.getBuildIdsFromJobId)._mock.setReturn([2], 1)
        mock.mockMethod(handle.BuildImages.printImageUrlsForBuild)
        handle.BuildImages.printImageUrlsForJob(1)
        handle.BuildImages.printImageUrlsForBuild._mock.assertCalled(2)

    def testPrintImageUrlsForBuild(self):
        handle = self.getRbuildHandle()
        mock.mockMethod(handle.ui.info)
        mock.mockMethod(handle.facade.rbuilder.getBuildFiles)._mock.setReturn([{}], 1)
        handle.BuildImages.printImageUrlsForBuild(1)
        self.assertEquals(
            [x[0][0]%x[0][1:] for x in handle.ui.info._mock.calls],
            ['Build 1\tNoFileName\t0\tNoURL'])
        handle.ui.info._mock.popCall()

        handle.facade.rbuilder.getBuildFiles._mock.setReturn([
            {'downloadUrl': 'http://foo',
             'fileId': 1234,
             'baseFileName': 'foo.iso'}], 1)
        handle.BuildImages.printImageUrlsForBuild(1)
        self.assertEquals(
            [x[0][0]%x[0][1:] for x in handle.ui.info._mock.calls],
            ['Build 1\tfoo.iso\t1234\thttp://foo'])
        handle.ui.info._mock.popCall()


