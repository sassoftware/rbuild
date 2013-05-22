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

import tempfile

from rbuild_test import rbuildhelp
from testutils import mock

from conary.versions import VersionFromString as VFS
from conary.deps import deps

from rbuild import errors
from rbuild.productstore import dirstore



class InitTest(rbuildhelp.RbuildHelper):
    def testInitCommandParsing(self):
        handle = self.getRbuildHandle()
        handle.Init.registerCommands()
        handle.Init.initialize()
        cmd = handle.Commands.getCommandClass('init')()
        mock.mock(cmd, '_initCommand')
        cmd.runCommand(handle, {}, ['rbuild', 'init', 'foo', '1'])
        cmd._initCommand._mock.assertCalled(handle, 'foo', '1')

        mock.mock(cmd, '_initByLabelCommand')
        cmd.runCommand(handle, {}, ['rbuild', 'init', 'localhost@rpl:foo-1'])
        cmd._initByLabelCommand._mock.assertCalled(handle,
                                                   'localhost@rpl:foo-1')

        # too few arguments
        self.assertRaises(errors.ParseError, 
                cmd.runCommand, handle, {}, 
                    ['rbuild', 'init'])
        # too many arguments
        self.assertRaises(errors.ParseError, 
                cmd.runCommand, handle, {}, 
                ['rbuild', 'init', 'localhost@rpl:1', 'a', 'b', 'c', 'd'])

    def testInitCommands(self):
        handle = self.getRbuildHandle()
        handle.Init.registerCommands()
        handle.Init.initialize()
        cmd = handle.Commands.getCommandClass('init')()
        mock.mockMethod(handle.Init.getProductVersionByLabel)
        mock.mockMethod(handle.Init.getProductVersionByParts)
        mock.mockMethod(handle.Init.createProductDirectory)
        handle.Init.getProductVersionByLabel._mock.setDefaultReturn(
                                                '/localhost@rpl:foo-1/1.0-1')
        handle.Init.getProductVersionByParts._mock.setReturn(
                                                '/localhost@rpl:foo-1/1.0-2',
                                                'foo', '1')
        rc = cmd._initByLabelCommand(handle, 'localhost@rpl:foo-1')
        assert(not rc)
        handle.Init.createProductDirectory._mock.assertCalled(
                                                '/localhost@rpl:foo-1/1.0-1')
        rc = cmd._initCommand(handle, 'foo', '1')
        assert(not rc)
        handle.Init.createProductDirectory._mock.assertCalled(
                                                '/localhost@rpl:foo-1/1.0-2')


    def testGetProductStoreByParts(self):
        handle = self.getRbuildHandle()
        mock.mockMethod(handle.Init.getProductVersionByLabel)
        rbuilderFacade = handle.facade.rbuilder
        m = mock.mockMethod(rbuilderFacade.getProductLabelFromNameAndVersion)
        m._mock.setReturn('foo.rpath.org@rpl:foo-1', 'foo', '1')

        handle.Init.getProductVersionByParts('foo', '1')
        handle.Init.getProductVersionByLabel._mock.assertCalled(
                                            'foo.rpath.org@rpl:foo-1')

    def testGetProductStoreByLabel(self):
        from rbuild_plugins import init
        co = init.Init('init', None, None)
        co.setHandle(mock.MockObject())
        returnTuple = ('product-definition:source', 
                       VFS('/foo.rpath.org@rpl:proddef-1/1.0-1'), deps.Flavor())
        co.handle.facade.conary._findTrove._mock.setReturn(returnTuple,
                    'product-definition:source',
                    'foo.rpath.org@rpl:proddef-1')
        assert(co.getProductVersionByLabel('foo.rpath.org@rpl:proddef-1') 
                == '/foo.rpath.org@rpl:proddef-1/1.0-1')

    def testCheckProductCheckout(self):
        self.getRbuildHandle()
        from rbuild_plugins import init
        class Stage(object):
            def __init__(self, name):
                self.name = name
        os.chdir(self.workDir)
        co = init.Init('init', None, None)
        handle = mock.MockObject(stableReturnValues=True)
        co.setHandle(handle)

        #pylint: disable-msg=W0622
        def mkdtemp(dir):
            os.mkdir(dir + '/temp')
            return dir + '/temp'
        self.mock(tempfile, 'mkdtemp', mkdtemp)
        handle.product.getProductShortname._mock.setReturn('foo')
        handle.product.getProductVersion._mock.setReturn('1')
        handle.product.getStages._mock.setReturn([Stage('devel'),
                                                  Stage('stable')])
        handle.product.getLabelForStage._mock.setReturn(
            'localhost@rpl:1-devel', 'devel')
        handle.product.getLabelForStage._mock.setReturn(
            'localhost@rpl:1', 'stable')
        productStore = mock.MockObject()
        productStore.getProduct._mock.setReturn(handle.product)
        mock.mock(dirstore, 'CheckoutProductStore', returnValue=productStore)

        # actual function call
        co.createProductDirectory('/localhost@rpl:1/1.0-1')

        # tests of result
        handle.facade.conary.checkout._mock.assertCalled(
                 'product-definition',
                 '/localhost@rpl:1/1.0-1',
                 targetDir=self.workDir + '/temp/.rbuild/product-definition')
        directories = [x[0][1] for x in dirstore.CheckoutProductStore._mock.calls]
        self.assertEquals(directories,
                          [self.workDir+'/temp', 'foo-1'])

        self.assertEquals(file(self.workDir+'/foo-1/devel/conaryrc').read(),
            '# This file may be automatically overwritten by rbuild\n'
            'buildLabel localhost@rpl:1-devel\n'
            'installLabelPath localhost@rpl:1-devel\n')
        self.assertEquals(file(self.workDir+'/foo-1/stable/conaryrc').read(),
            '# This file may be automatically overwritten by rbuild\n'
            'buildLabel localhost@rpl:1\n'
            'installLabelPath localhost@rpl:1\n')

        err = self.assertRaises(errors.PluginError, co.createProductDirectory,
                                '/localhost@rpl:1/1.0-1')
        assert(str(err) == "Directory 'foo-1' already exists.")

        co.createProductDirectory('/localhost@rpl:1/1.0-1', productDir='foo2')
        assert(os.path.exists(self.workDir + '/foo2/devel/.stage'))
        assert(os.path.exists(self.workDir + '/foo-1/devel/.stage'))

