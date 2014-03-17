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


class StatusTest(rbuildhelp.RbuildHelper):
    def testStatusCommandArgParsing(self):
        self.getRbuildHandle() # required for test to run alone
        self.checkRbuild('status --concise --all --product',
            'rbuild_plugins.status.StatusCommand.runCommand',
            [None, None, {'concise' : True,
                          'all' : True,
                          'product' : True},
            ['rbuild', 'status']])
        self.checkRbuild('status --verbose --no-product',
            'rbuild_plugins.status.StatusCommand.runCommand',
            [None, None, {'verbose' : True,
                          'no-product' : True},
            ['rbuild', 'status']])
        self.checkRbuild('status --local',
            'rbuild_plugins.status.StatusCommand.runCommand',
            [None, None, {'local' : True},
            ['rbuild', 'status']])
        self.checkRbuild('status --repository',
            'rbuild_plugins.status.StatusCommand.runCommand',
            [None, None, {'repository' : True},
            ['rbuild', 'status']])

    def testStatusCommandParsing(self):
        handle = self.getRbuildHandle()
        from rbuild_plugins import status
        handle.Status.registerCommands()
        handle.Status.initialize()
        cmd = handle.Commands.getCommandClass('status')()
        mock.mockMethod(handle.Status.printDirectoryStatus)
        mock.mock(dirstore, 'getDefaultProductDirectory')
        mock.mock(handle.facade.conary, 'isConaryCheckoutDirectory')
        cwd = os.getcwd()

        dirstore.getDefaultProductDirectory._mock.setDefaultReturn('asdf')
        handle.facade.conary.isConaryCheckoutDirectory._mock.setDefaultReturn(
            False)
        cmd.runCommand(handle, {'all': True}, ['rbuild', 'status'])
        handle.Status.printDirectoryStatus._mock.assertCalled('asdf',
            verbosity=status.DEFAULT, product=True,
            local=True, repository=True)
        handle.facade.conary.isConaryCheckoutDirectory._mock.assertCalled(cwd)

        dirstore.getDefaultProductDirectory._mock.setDefaultReturn('blah')
        handle.facade.conary.isConaryCheckoutDirectory._mock.setDefaultReturn(
            False)
        cmd.runCommand(handle, {'no-product': True, 'concise': True},
                       ['rbuild', 'status', 'asdf'])
        handle.Status.printDirectoryStatus._mock.assertCalled('asdf',
            verbosity=status.CONCISE, product=False,
            local=True, repository=True)
        handle.facade.conary.isConaryCheckoutDirectory._mock.assertCalled(cwd)

        handle.facade.conary.isConaryCheckoutDirectory._mock.setDefaultReturn(
            True)
        cmd.runCommand(handle, {'verbose': True},
                       ['rbuild', 'status'])
        handle.Status.printDirectoryStatus._mock.assertCalled(cwd,
            verbosity=status.VERBOSE, product=False,
            local=True, repository=True)

        handle.facade.conary.isConaryCheckoutDirectory._mock.setDefaultReturn(
            True)
        cmd.runCommand(handle, {'local': True},
                       ['rbuild', 'status'])
        handle.Status.printDirectoryStatus._mock.assertCalled(cwd,
            verbosity=status.DEFAULT, product=False,
            local=True, repository=False)

        handle.facade.conary.isConaryCheckoutDirectory._mock.setDefaultReturn(
            True)
        cmd.runCommand(handle, {'repository': True},
                       ['rbuild', 'status'])
        handle.Status.printDirectoryStatus._mock.assertCalled(cwd,
            verbosity=status.DEFAULT, product=False,
            local=False, repository=True)

    def testPrintDirectoryStatus(self):
        handle = self.getRbuildHandle()
        from rbuild_plugins import status
        mock.mockMethod(handle.Status._printOneDirectoryStatus)
        mock.mock(dirstore, 'CheckoutProductStore')
        dirstore.CheckoutProductStore().getProductDefinitionDirectory._mock.setDefaultReturn('/full/path/.rbuild/product-definition')
        dirstore.CheckoutProductStore().getBaseDirectory._mock.setDefaultReturn('/full/path')

        handle.Status._printOneDirectoryStatus._mock.setDefaultReturn(None)
        self.mock(os, 'walk', lambda x: [
            ('/full/path', ['Development', '.rbuild'], False)])
        handle.Status.printDirectoryStatus('/full/path', product=True)
        self.unmock()
        handle.Status._printOneDirectoryStatus._mock.assertCalled(
            '/full/path/.rbuild/product-definition',
            'Product Definition', status.DEFAULT, proddef=True,
            local=True, repository=True)
        handle.Status._printOneDirectoryStatus._mock.assertCalled(
            '/full/path', '/full/path', status.DEFAULT, '',
            local=True, repository=True)
        handle.Status._printOneDirectoryStatus._mock.assertCalled(
            '/full/path/Development', 'Development', status.DEFAULT, None,
            local=True, repository=True)
        self.mock(os, 'walk', lambda x: [])
        handle.Status.printDirectoryStatus('bogus', product=True)
        self.unmock()
        handle.Status._printOneDirectoryStatus._mock.assertCalled(
            '/full/path/.rbuild/product-definition',
            'Product Definition', status.DEFAULT, proddef=True,
            local=True, repository=True)
        handle.Status._printOneDirectoryStatus._mock.assertCalled(
            'bogus', 'bogus', status.DEFAULT, '',
            local=True, repository=True)

        self.assertRaises(ValueError, handle.Status.printDirectoryStatus,
            'bogus', product=True, local=False, repository=False)

    def testPrintOneDirectoryStatus(self):
        self.initProductDirectory(self.workDir)
        os.chdir(self.workDir)
        handle = self.getRbuildHandle()
        from rbuild_plugins import status
        mock.mockMethod(handle.facade.conary.getCheckoutLog)
        mock.mock(dirstore, 'getStageNameFromDirectory')
        mock.mock(handle.facade.conary, 'isConaryCheckoutDirectory')

        outputList = []
        def captureOutput(k, msg, *args):
            outputList.append('%s' % (msg % args, ))
        self.mock(ui.UserInterface, 'write', captureOutput)

        # No changes, no product, no noise
        handle.facade.conary.isConaryCheckoutDirectory._mock.setDefaultReturn(
            False)
        handle.facade.conary.getCheckoutLog._mock.setDefaultReturn(['nothing has been committed'])
        dirstore.getStageNameFromDirectory._mock.setDefaultReturn('devel')
        handle.Status.printDirectoryStatus('.')
        self.assertEquals(outputList, [])


        os.chdir('devel')
        self.newpkg('NewPackage')
        os.chdir(self.workDir)
        handle.facade.conary.isConaryCheckoutDirectory._mock.setDefaultReturn(
            True)
        mock.mockMethod(handle.facade.conary.getCheckoutStatus)
        mock.mockMethod(handle.facade.conary.iterCheckoutDiff)
        handle.facade.conary.getCheckoutStatus._mock.setDefaultReturn(
            [('A', 'NewPackage.recipe')])
        handle.facade.conary.iterCheckoutDiff._mock.setDefaultReturn(
            ['+++ NewPackage.recipe', '--- /dev/null', '+the recipe text'])
        pendingAnnounce = handle.Status._printOneDirectoryStatus('.',
            'NewPackage', status.VERBOSE, pendingAnnounce='', repository=False)
        expectedTxt = [
            '\n',
            'devel stage status:\n===================',
            'L-  NewPackage',
            '  * Local changes not committed to repository:',
            'L-  A   NewPackage/NewPackage.recipe',
            '+++ NewPackage.recipe',
            '--- /dev/null',
            '+the recipe text',
        ]
        self.assertEquals(outputList, expectedTxt)
        del outputList[:]
        self.assertEquals(pendingAnnounce, 'devel')

        mock.mockMethod(handle.facade.conary._getNewerRepositoryVersions)
        handle.facade.conary._getNewerRepositoryVersions._mock.setDefaultReturn(
            ['0.1'])
        handle.facade.conary.getCheckoutLog._mock.setDefaultReturn(
            ['fake log message'])
        mock.mockMethod(handle.facade.conary.iterRepositoryDiff)
        handle.facade.conary.iterRepositoryDiff._mock.setDefaultReturn(
            ['fake repository diff'])
        handle.Status._printOneDirectoryStatus('.', 'NewPackage',
            status.VERBOSE, pendingAnnounce='devel', local=False)
        expectedTxt = [
            '-R  NewPackage',
            '  * Remote repository commit messages for newer versions:',
            '-R  fake log message',
            'fake repository diff'
        ]
        del outputList[:]

        # just pretend this is a product checkout...
        handle.facade.conary.getCheckoutStatus._mock.setDefaultReturn(
            [('M', 'product-definition.xml')])
        mock.mockMethod(handle.product.getProductName)
        mock.mockMethod(handle.product.getProductVersion)
        handle.product.getProductName._mock.setDefaultReturn('1')
        handle.product.getProductVersion._mock.setDefaultReturn('2')
        handle.Status._printOneDirectoryStatus('.', 'Product Definition',
            status.CONCISE, proddef=True, repository=False)
        expectedTxt = [
            'Product 1-2 status:\n===================',
            'L-  Product Definition',
        ]
        self.assertEquals(outputList, expectedTxt)

    def testMacroInComment(self):
        self.initProductDirectory(self.workDir)
        os.chdir(self.workDir)
        handle = self.getRbuildHandle()
        from rbuild_plugins import status
        mock.mockMethod(handle.facade.conary.getCheckoutLog)
        mock.mock(dirstore, 'getStageNameFromDirectory')
        mock.mock(handle.facade.conary, 'isConaryCheckoutDirectory')
        dirstore.getStageNameFromDirectory._mock.setDefaultReturn('devel')

        outputList = []
        def captureOutput(k, msg, *args):
            outputList.append('%s' % (msg % args, ))
        self.mock(ui.UserInterface, 'write', captureOutput)

        os.chdir('devel')
        self.newpkg('NewPackage')
        os.chdir(self.workDir)
        handle.facade.conary.isConaryCheckoutDirectory._mock.setDefaultReturn(
            True)
        mock.mockMethod(handle.facade.conary.getCheckoutStatus)
        mock.mockMethod(handle.facade.conary.iterCheckoutDiff)
        handle.facade.conary.getCheckoutStatus._mock.setDefaultReturn(
            [('A', 'NewPackage.recipe')])
        handle.facade.conary.iterCheckoutDiff._mock.setDefaultReturn(
            ['+++ NewPackage.recipe', '--- /dev/null', '+the %(recipe)s text'])
        pendingAnnounce = handle.Status._printOneDirectoryStatus('.',
            'NewPackage', status.VERBOSE, pendingAnnounce='', repository=False)
        expectedTxt = [
            '\n',
            'devel stage status:\n===================',
            'L-  NewPackage',
            '  * Local changes not committed to repository:',
            'L-  A   NewPackage/NewPackage.recipe',
            '+++ NewPackage.recipe',
            '--- /dev/null',
            '+the %(recipe)s text',
        ]
        self.assertEquals(outputList, expectedTxt)
        del outputList[:]
        self.assertEquals(pendingAnnounce, 'devel')
