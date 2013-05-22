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



import datetime

from rbuild import errors
from rbuild_test import rbuildhelp
from testutils import mock

class BuildReleaseTest(rbuildhelp.RbuildHelper):
    def testCommandParsing(self):
        handle = self.getRbuildHandle()
        handle.Build.registerCommands()
        handle.Build.initialize()
        handle.BuildRelease.initialize()
        cmd = handle.Commands.getCommandClass('build')()
        mock.mockMethod(handle.Build.watchJob)
        mock.mockMethod(handle.facade.rmake.isJobBuilt, True)
        mock.mockMethod(handle.BuildRelease.buildRelease, 1)
        handle.productStore = mock.MockObject()
        handle.productStore.getImageJobId._mock.setDefaultReturn(42)
        handle.product = mock.MockObject()
        cmd.runCommand(handle, {}, ['rbuild', 'build', 'release'])
        handle.productStore.setStageReleaseId._mock.assertCalled(0)
        handle.BuildRelease.buildRelease._mock.assertCalled(42,
            name=None, version=None, description=None)

        cmd.runCommand(handle, {'release-name':'asdf',
                                'release-version':'vername',
                                'release-description':'reldesc'},
                                ['rbuild', 'build', 'release'])
        handle.BuildRelease.buildRelease._mock.assertCalled(42,
            name='asdf', version='vername', description='reldesc')
        handle.productStore.setStageReleaseId._mock.assertCalled(0)

        handle.facade.rmake.isJobBuilt._mock.setDefaultReturn(False)
        self.assertRaises(errors.PluginError,
            cmd.runCommand, handle, {}, ['rbuild', 'build', 'release'])
        handle.productStore.setStageReleaseId._mock.assertNotCalled()

        handle.productStore.getImageJobId._mock.setDefaultReturn(None)
        self.assertRaises(errors.PluginError,
            cmd.runCommand, handle, {}, ['rbuild', 'build', 'release'])
        handle.productStore.setStageReleaseId._mock.assertNotCalled()

    def testCommand(self):
        handle = self.getRbuildHandle()
        self.checkRbuild('build release',
            'rbuild_plugins.buildrelease.BuildReleaseCommand.runCommand',
            [None, None, {},
            ['build', 'release']])

    def testBuildRelease(self):
        handle = self.getRbuildHandle()
        rc = handle.BuildRelease.buildRelease(None)
        assert(rc is None)

        mock.mock(handle.facade, 'rmake')
        mock.mock(handle.facade, 'rbuilder')
        mock.mock(handle, 'productStore')
        mock.mock(handle, 'product')
        handle.facade.rmake.getBuildIdsFromJobId._mock.setDefaultReturn(
            [1, 2, 3])
        handle.facade.rbuilder.createRelease._mock.setDefaultReturn(43)
        handle.facade.rbuilder.getReleaseUrl._mock.setDefaultReturn('http://somewhere')
        handle.productStore.getActiveStageName._mock.setDefaultReturn('teststage')
        handle.product.getProductVersion._mock.setDefaultReturn('1.0')
        handle.product.getProductDescription._mock.setDefaultReturn('')
        user = ['admin', 'password']
        userObj = mock.MockObject()
        userObj._mock.set(user=user)
        mock.mockMethod(handle.getConfig, userObj)
        data = {'name':'teststage images', 'version':'1.0', 
                'description':'Release built by admin on NOW'}
        handle.facade.rbuilder.updateRelease._mock.setDefaultReturn(None)

        mock.mock(handle.BuildRelease, '_getTimeString')
        handle.BuildRelease._getTimeString._mock.setReturn('NOW')
        rc, _ = self.captureOutput(handle.BuildRelease.buildRelease, 42)
        expectedTxt = '''\
Created release "teststage images", release id 43
'''
#Release 43\tteststage images\thttp://somewhere
        handle.ui.outStream.write._mock.assertCalled(expectedTxt)
        handle.facade.rmake.getBuildIdsFromJobId._mock.assertCalled(42)
        handle.facade.rbuilder.createRelease._mock.assertCalled([1, 2, 3])
        handle.productStore.getActiveStageName._mock.assertCalled()
        handle.product.getProductVersion._mock.assertCalled()
        handle.facade.rbuilder.updateRelease._mock.assertCalled(43, **data)
        handle.productStore.setStageReleaseId._mock.assertCalled(43)
        self.assertEquals(rc, 43)

        handle.product.getProductDescription._mock.setDefaultReturn(
            'This Is A Description')
        data['description'] = 'This Is A Description'
        handle.BuildRelease.buildRelease(42)
        handle.ui.outStream.write._mock.assertCalled(expectedTxt)
        handle.facade.rbuilder.updateRelease._mock.assertCalled(43, **data)

    def testGetTimeString(self):
        handle = self.getRbuildHandle()
        timestring = handle.BuildRelease._getTimeString()
        # assert something meaningful that won't change any time soon,
        # since we can't mock datetime.datetime.now()
        self.assertEquals(len(timestring), 24)
        

