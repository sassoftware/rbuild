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

import sys
from rbuild import errors
from rbuild_test import rbuildhelp
from StringIO import StringIO
from testutils import mock


class BuildImagesTest(rbuildhelp.RbuildHelper):
    def testCommandParsing(self):
        handle = self.getRbuildHandle()
        handle.Build.registerCommands()
        handle.Build.initialize()
        handle.BuildImages.initialize()
        cmd = handle.Commands.getCommandClass('build')()
        mock.mockMethod(handle.BuildImages.buildImages, [1])
        mock.mockMethod(handle.facade.rbuilder.watchImages)
        mock.mockMethod(handle.BuildImages.printImageUrlsForBuild)

        err = self.assertRaises(errors.MissingProductStoreError,
                                cmd.runCommand, handle, {},
                                ['rbuild', 'build', 'images'])
        self.assertIn('rbuild init', str(err))

        mock.mock(handle, 'productStore')
        handle.productStore._mock.set(_currentStage=None)

        err = self.assertRaises(errors.MissingActiveStageError,
                                cmd.runCommand, handle, {},
                                ['rbuild', 'build', 'images'])
        self.assertIn('valid stage', str(err))

        handle.productStore._mock.set(_currentStage='stage')

        handle.product = mock.MockObject()
        cmd.runCommand(handle, {}, ['rbuild', 'build', 'images'])
        handle.BuildImages.buildImages._mock.assertCalled(None)
        handle.facade.rbuilder.watchImages._mock.assertCalled([1])
        handle.BuildImages.printImageUrlsForBuild._mock.assertCalled(1)

        cmd.runCommand(handle, {}, ['rbuild', 'build', 'images', 'image 1', 'image 2'])
        handle.BuildImages.buildImages._mock.assertCalled(['image 1', 'image 2'])

        handle.facade.rbuilder.watchImages._mock.setReturn(False, [1])
        rv = cmd.runCommand(handle, {}, ['rbuild', 'build', 'images'])
        self.assertEqual(rv, 10)

        self.mock(sys, 'stdout', StringIO())
        cmd.runCommand(handle, {'no-watch':True},
            ['rbuild', 'build', 'images'])
        self.assertEqual(sys.stdout.getvalue(), '1\n')

    def testBuildAllImages(self):
        handle = self.getRbuildHandle()
        handle.productStore = mock.MockObject()
        handle.product = mock.MockObject()
        mock.mockMethod(handle.Build.warnIfOldProductDefinition)
        mock.mockMethod(handle.facade.rbuilder.buildAllImagesForStage, [1])
        rc = handle.BuildImages.buildImages()
        self.assertEqual(rc, [1])
        handle.facade.rbuilder.buildAllImagesForStage._mock.assertCalled(
                buildNames=None)
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


