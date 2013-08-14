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


class Rebase(rbuildhelp.RbuildHelper):
    def testRebaseCommandParsing(self):
        handle = self.getRbuildHandle(mock.MockObject())
        handle.Rebase.registerCommands()
        handle.Rebase.initialize()
        cmd = handle.Commands.getCommandClass('rebase')()
        mock.mockMethod(handle.Rebase.rebaseProduct)
        cmd.runCommand(handle, {}, ['rbuild', 'rebase', 'localhost@rpl:1'])
        handle.Rebase.rebaseProduct._mock.assertCalled(
            interactive=False, label='localhost@rpl:1', test=False)
        cmd.runCommand(handle, {}, ['rbuild', 'rebase'])
        handle.Rebase.rebaseProduct._mock.assertCalled(
            interactive=False, label=None, test=False)

    def testRebaseCommandArgParsing(self):
        self.getRbuildHandle()
        self.checkRbuild('rebase --interactive',
            'rbuild_plugins.rebase.RebaseCommand.runCommand',
            [None, None, {'interactive' : True},
            ['rbuild', 'rebase']])
        self.checkRbuild('rebase --test',
            'rbuild_plugins.rebase.RebaseCommand.runCommand',
            [None, None, {'test' : True},
            ['rbuild', 'rebase']])

    def testRebaseProduct(self):
        handle = self.getRbuildHandle(mock.MockObject())
        mock.mock(handle, 'ui')
        mock.mockMethod(handle.facade.conary._getConaryClient)
        conaryClient = handle.facade.conary._getConaryClient()
        handle.product = mock.MockObject()
        handle.product._mock.set(preMigrateVersion='2.0')
        platVers = [
            'platform-definition=/conary.rpath.com@rpl:2/1.0-1',
            'platform-definition=/conary.rpath.com@rpl:2/1.1-2']
        handle.product.getPlatformSourceTrove._mock.setReturns(platVers)
        mock.mockMethod(handle.Rebase._getrBuilderProductDefinitionSchemaVersion)
        handle.Rebase._getrBuilderProductDefinitionSchemaVersion._mock.setDefaultReturn('4.0')
        mock.mockMethod(handle.Rebase._raiseErrorIfModified)
        handle.Rebase._raiseErrorIfModified._mock.setDefaultReturn(None)
        mock.mockMethod(handle.Rebase._raiseErrorIfConflicts)
        handle.Rebase._raiseErrorIfConflicts._mock.setDefaultReturn(None)
        handle.productStore.getProductDefinitionDirectory._mock.setDefaultReturn('/proddir')

        handle.Rebase.rebaseProduct(label='localhost@rpl:1')
        handle.product.rebase._mock.assertCalled(conaryClient,
                label='localhost@rpl:1', schemaVersion='4.0')
        handle.product.saveToRepository._mock.assertCalled(conaryClient,
            version='4.0')
        # should be called twice (RBLD-155)
        handle.productStore.update._mock.assertCalled()
        handle.productStore.update._mock.assertCalled()
        handle.Rebase._getrBuilderProductDefinitionSchemaVersion._mock.assertCalled('2.0')
        # should be called once (RBLD-164)
        handle.Rebase._raiseErrorIfModified._mock.assertCalled('/proddir')
        # should be called two times (RBLD-164)
        handle.Rebase._raiseErrorIfConflicts._mock.assertCalled('/proddir')
        handle.Rebase._raiseErrorIfConflicts._mock.assertCalled('/proddir')
        handle.ui.info._mock.assertCalled(
            'Update %s -> %s', platVers[0], platVers[1].split('/')[-1])

        # test a rebase to a new platform
        platVers = [
            'platform-definition=/conary.rpath.com@rpl:2/1.0-1',
            'platform-definition=/unrelated.foobar.com@rpl:2/1.1-2']
        handle.product.getPlatformSourceTrove._mock.setReturns(platVers)
        handle.Rebase.rebaseProduct(label='unrelated.foobar.com@rpl:2')
        handle.ui.info._mock.assertCalled(
            'Update %s -> %s', platVers[0], platVers[1].split('=')[-1][1:])

        class sp:
            def __init__(self, n,l,v):
                self.troveName = n
                self.label = l
                self.version = v

        # test searchPath change with no platdef change (RBLD-316)
        handle.product.saveToRepository._mock.popCall()
        platVers = [
            'platform-definition=/conary.rpath.com@rpl:2/1.1-3',
            'platform-definition=/conary.rpath.com@rpl:2/1.1-3']
        handle.product.getPlatformSourceTrove._mock.setReturns(platVers)

        searchPaths = [
            (sp('group-foo', 'a@b:c', '1'), sp('group-bar', 'd@e:f', '1')),
            (sp('group-foo', 'a@b:c', '2'), sp('group-bar', 'd@e:f', '3')),
        ]
        handle.product.getSearchPaths._mock.setReturns(searchPaths)
        handle.Rebase.rebaseProduct(test=True)
        handle.ui.info._mock.assertCalled(
            'Update search path from:\n%s\nto:\n%s',
            '    group-foo=a@b:c/1\n'
            '    group-bar=d@e:f/1',
            '    group-foo=a@b:c/2\n'
            '    group-bar=d@e:f/3'
        )
        handle.product.saveToRepository._mock.assertNotCalled()

        # test searchPath change with platdef change (RBLD-316)
        platVers = [
            'platform-definition=/conary.rpath.com@rpl:2/1.1-3',
            'platform-definition=/conary.rpath.com@rpl:2/1.1-4']
        handle.product.getPlatformSourceTrove._mock.setReturns(platVers)
        searchPaths = [
            (sp('group-foo', 'a@b:c', '1'), sp('group-bar', 'd@e:f', '1')),
            (sp('group-foo', 'a@b:c', '2'), sp('group-bar', 'd@e:f', '3')),
        ]
        handle.product.getSearchPaths._mock.setReturns(searchPaths)
        handle.ui.getYn._mock.setDefaultReturn(False)
        handle.product.saveToRepository._mock.assertNotCalled()
        handle.Rebase.rebaseProduct(interactive=True)
        handle.ui.info._mock.assertCalled(
            'Update search path from:\n%s\nto:\n%s',
            '    group-foo=a@b:c/1\n'
            '    group-bar=d@e:f/1',
            '    group-foo=a@b:c/2\n'
            '    group-bar=d@e:f/3'
        )
        handle.ui.info._mock.assertCalled(
            'Update %s -> %s', platVers[0], platVers[1].split('/')[-1])
        handle.ui.info._mock.assertNotCalled()
        handle.product.saveToRepository._mock.assertNotCalled()

    def testOldProddefSchemaHandling(self):
        # This test will need to be removed when rpath-product-definition
        # 4.0 is fully retired and the tested backward compatibility code
        # is removed from rbuild.
        # Lots of work required to avoid preMigrateVersion existing...
        handle = self.getRbuildHandle(mock.MockObject())
        class product: pass
        handle.productStore = mock.MockObject()
        handle.product = product()
        handle.product.rebase = mock.MockObject()
        handle.product.saveToRepository = mock.MockObject()
        handle.product.getPlatformSourceTrove = mock.MockObject()
        handle.product.getSearchPaths = mock.MockObject()
        handle.facade = mock.MockObject()
        conaryClient = handle.facade.conary._getConaryClient()
        mock.mockMethod(handle.Rebase._raiseErrorIfConflicts)
        handle.Rebase.rebaseProduct()
        handle.product.saveToRepository._mock.assertCalled(conaryClient)

    def testRaiseErrorIfProddefSchemaIncompatible(self):
        handle = self.getRbuildHandle()
        from rbuild_plugins.rebase import proddef
        from rbuild_plugins.rebase import IncompatibleProductDefinitionError
        from rbuild_plugins.rebase import OlderProductDefinitionError
        rbuilder = handle.facade.rbuilder

        mock.mockMethod(rbuilder.getProductDefinitionSchemaVersion)
        mock.mock(proddef, 'ProductDefinition')
        proddef.ProductDefinition._mock.set(version='4.0')

        # client newer than server, no change in schema version
        rbuilder.getProductDefinitionSchemaVersion._mock.setReturn('2.0')
        self.failUnlessEqual('2.0',
            handle.Rebase._getrBuilderProductDefinitionSchemaVersion('2.0'))
        # client newer than server, change in schema version
        self.failUnlessEqual('2.0',
            handle.Rebase._getrBuilderProductDefinitionSchemaVersion('1.0'))

        # client same version as server
        rbuilder.getProductDefinitionSchemaVersion._mock.setReturn('4.0')
        self.failUnlessEqual('4.0',
            handle.Rebase._getrBuilderProductDefinitionSchemaVersion('4.0'))

        # client older than server
        rbuilder.getProductDefinitionSchemaVersion._mock.setReturn('5.0')
        self.failUnlessRaises(OlderProductDefinitionError,
            handle.Rebase._getrBuilderProductDefinitionSchemaVersion,
            '4.0')
        self.failUnlessRaises(IncompatibleProductDefinitionError,
            handle.Rebase._getrBuilderProductDefinitionSchemaVersion,
            '4.0')

    def testRaiseErrorIfModified(self):
        handle = self.getRbuildHandle(mock.MockObject())
        from rbuild_plugins.rebase import ModifiedFilesError
        mock.mockMethod(handle.Rebase._modifiedFileNames)
        handle.Rebase._modifiedFileNames._mock.setDefaultReturn('/proddir/1')
        self.assertRaises(ModifiedFilesError,
            handle.Rebase._raiseErrorIfModified, '/proddir')
        handle.Rebase._modifiedFileNames._mock.setDefaultReturn(None)
        handle.Rebase._raiseErrorIfModified('/proddir')

    def testRaiseErrorIfConflicts(self):
        handle = self.getRbuildHandle(mock.MockObject())
        from rbuild_plugins.rebase import FileConflictsError
        mock.mockMethod(handle.Rebase._fileConflictNames)
        handle.Rebase._fileConflictNames._mock.setDefaultReturn(
            ['/proddir/1.conflicts'])
        self.assertRaises(FileConflictsError,
            handle.Rebase._raiseErrorIfConflicts, '/proddir')
        handle.Rebase._fileConflictNames._mock.setDefaultReturn(None)
        handle.Rebase._raiseErrorIfConflicts('/proddir')

    def testModifiedFileNames(self):
        handle = self.getRbuildHandle()
        cf = handle.facade.conary
        mock.mockMethod(cf.getCheckoutStatus)
        cf.getCheckoutStatus._mock.setReturn((('A', '/p/1'), ('M', '/p/2')),
                                             '/p')
        self.assertEquals(handle.Rebase._modifiedFileNames('/p'), ['/p/2'])

    def testFileConflictNames(self):
        handle = self.getRbuildHandle()
        file(self.workDir+'/foo', 'w')
        file(self.workDir+'/foo.conflicts', 'w')
        self.assertEquals(handle.Rebase._fileConflictNames(self.workDir),
                          ['foo.conflicts'])
        


