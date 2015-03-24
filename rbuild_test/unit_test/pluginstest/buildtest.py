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

from testutils import mock

from rbuild import errors
from rbuild import ui
from rbuild.productstore import dirstore
from rbuild.productstore import abstract

class BuildTest(rbuildhelp.RbuildHelper):
    '''
    Test core plugins.build methods shared among build sub-plugins
    '''

    def testWatchAndCommitJob(self):
        handle = self.getRbuildHandle()
        mock.mockMethod(handle.facade.rmake.watchAndCommitJob)
        handle.facade.rmake.watchAndCommitJob._mock.setReturn(3, 1, None)
        ret = handle.Build.watchAndCommitJob(1)
        handle.facade.rmake.watchAndCommitJob._mock.assertCalled(1, None)
        self.assertEquals(ret, 3)
        handle.facade.rmake.watchAndCommitJob._mock.setReturn(2, 1, 'message')
        ret = handle.Build.watchAndCommitJob(1, 'message')
        handle.facade.rmake.watchAndCommitJob._mock.assertCalled(1, 'message')
        self.assertEquals(ret, 2)

    def testWatchJob(self):
        handle = self.getRbuildHandle()
        mock.mockMethod(handle.facade.rmake.watchJob)
        handle.facade.rmake.watchJob._mock.setReturn(2, 1)
        ret = handle.Build.watchJob(1)
        handle.facade.rmake.watchJob._mock.assertCalled(1)
        self.assertEquals(ret, 2)

    def testWarnIfOldProductDefinition(self):
        self.initProductDirectory(self.workDir)
        os.chdir(self.workDir)
        handle = self.getRbuildHandle(productStore=mock.MockObject())
        from rbuild_plugins import build as build_plugin
        proddefDir = self.workDir + '/.rbuild/product-definition'
        handle.productStore.getProductDefinitionDirectory._mock.setDefaultReturn(proddefDir)

        outputList = []
        def captureOutput(k, msg='', *args):
            outputList.append('%s' % (msg % args, ))
        self.mock(ui.UserInterface, 'write', captureOutput)

        mock.mockMethod(handle.facade.conary._getNewerRepositoryVersions)
        handle.product.getProductName._mock.setReturn('adsf')

        mock.mock(handle.facade.conary, '_getNewerRepositoryVersions')
        handle.facade.conary._getNewerRepositoryVersions._mock.setDefaultReturn(
            None)
        handle.Build.warnIfOldProductDefinition('foo')
        self.assertEquals(outputList, [])

        handle.facade.conary._getNewerRepositoryVersions._mock.setDefaultReturn(
            ['0', '1'])

        mock.mockMethod(handle.ui.getYn)
        handle.ui.getYn._mock.setDefaultReturn(True)
        handle.Build.warnIfOldProductDefinition('foo', display=False)
        self.assertEquals(outputList, [
            'The local copy of the adsf product definition is out of date',
            'If any of the newer changes may affect you, answer "no",',
            'and run the command "rbuild update product" to update',
            'your local copy of the product definition.',
            '',
        ])
        handle.ui.getYn._mock.assertCalled('Proceed with foo, ignoring differences in product definition?', default=True)

        del outputList[:]
        mock.mockMethod(handle.facade.conary.iterRepositoryDiff)
        handle.facade.conary.iterRepositoryDiff._mock.setReturn(['DIFF'],
            proddefDir, '1')
        mock.mockMethod(handle.facade.conary.getCheckoutLog)
        handle.facade.conary.getCheckoutLog._mock.setReturn(['CHANGELOG'],
            proddefDir, versionList=['0', '1'])
        handle.ui.getYn._mock.setDefaultReturn(False)
        err = self.assertRaises(build_plugin.OutdatedProductDefinitionError,
            handle.Build.warnIfOldProductDefinition, 'foo')
        self.assertEquals(outputList, [
            'The local copy of the adsf product definition is out of date',
            'The following changes are committed to the repository,',
            'but are not included in your local copy:',
            '',
            'DIFF',
            '',
            'The following change messages describe the changes just displayed:',
            'CHANGELOG',
            '',
            'If any of the newer changes may affect you, answer "no",',
            'and run the command "rbuild update product" to update',
            'your local copy of the product definition.',
            '',
        ])
        self.assertEquals(str(err), 'adsf product definition out of date')
        handle.ui.getYn._mock.assertCalled('Proceed with foo, ignoring differences in product definition?', default=True)

        handle.productStore = abstract.ProductStore()
        self.assertEquals(handle.Build.warnIfOldProductDefinition('adsf'),
            None)


