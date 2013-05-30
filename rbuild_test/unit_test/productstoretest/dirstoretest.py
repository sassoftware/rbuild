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

from conary.lib import util
from conary import state

from rbuild import errors

from rpath_proddef import api1 as proddef
from rbuild.productstore import dirstore


class DirStoreTest(rbuildhelp.RbuildHelper):
    def _prepProductStore(self):
        os.chdir(self.workDir)
        util.mkdirChain('foo/.rbuild/product-definition')
        self.writeFile(
                    'foo/.rbuild/product-definition/product-definition.xml', '')
        util.mkdirChain('foo/stable')
        self.writeFile('foo/stable/.stage', 'stable\n')
        from rbuild.productstore import abstract
        mock.mock(abstract.ProductStore, 'checkStageIsValid')

    def testCheckoutProductStore(self):
        self._prepProductStore()
        util.mkdirChain('foo/stable/package')
        os.chdir('foo/stable/package')
        handle = self.getRbuildHandle(productStore=mock.MockObject())
        productStore = dirstore.CheckoutProductStore(handle)
        self.assertEquals(productStore.getBaseDirectory(),
            self.workDir + '/foo')
        self.assertEquals(productStore.getActiveStageName(), 'stable')
        productStore = dirstore.CheckoutProductStore(handle,
            baseDirectory=self.workDir + '/foo')
        self.assertEquals(productStore.getBaseDirectory(),
            self.workDir + '/foo')

    def testGetDefaultProductDirectory(self):
        self._prepProductStore()
        productDirectory = dirstore.getDefaultProductDirectory('foo/stable')
        # relative path
        self.assertEquals(productDirectory, 'foo')

        os.chdir('foo/stable')
        # starts with os.getcwd() so will be absolute path
        productDirectory = dirstore.getDefaultProductDirectory()
        self.assertEquals(productDirectory, self.workDir + '/foo')

        self.assertRaises(errors.MissingProductStoreError,
            dirstore.getDefaultProductDirectory, 'directoryDoesNotExist')

        os.chdir('/')
        self.assertRaises(errors.MissingProductStoreError,
            dirstore.getDefaultProductDirectory, error=True)

    def testGetStageNameFromDirectory(self):
        self._prepProductStore()
        stageName = dirstore.getStageNameFromDirectory('foo/stable')
        assert stageName == 'stable'
        os.chdir('foo/stable')
        stageName = dirstore.getStageNameFromDirectory('.')
        assert stageName == 'stable'
        stageName = dirstore.getStageNameFromDirectory()
        assert stageName == 'stable'

    def testProductStoreError(self):
        handle = self.getRbuildHandle()
        err = self.assertRaises(errors.RbuildError, 
                    dirstore.CheckoutProductStore, handle, self.workDir)
        assert(str(err) == "No product directory at '%s'" % self.workDir)
        err = self.assertRaises(errors.RbuildError, 
                    dirstore.CheckoutProductStore, handle)
        assert(str(err) == "Could not find product directory")

    def testCore(self):
        handle = self.getRbuildHandle()
        productClass = mock.MockObject(stableReturnValues=True)
        stage = mock.MockObject(label='localhost@rpl:1')
        productClass().getStage._mock.setReturn(stage, 'foo')
        productClass._mock.popCall()
        self.mock(proddef, 'ProductDefinition', productClass)
        os.chdir(self.workDir)
        util.mkdirChain('foo/.rbuild/product-definition')
        self.writeFile('foo/.rbuild/product-definition/product-definition.xml',
                       '')

        p = dirstore.CheckoutProductStore(handle, 'foo')
        err = self.assertRaises(errors.RbuildError, p.getActiveStageName)
        self.assertEquals(str(err), 'No current stage (setActiveStageName)')
        mock.mock(dirstore.CheckoutProductStore, 'checkStageIsValid')
        p.setActiveStageName('foo')
        assert(p.getActiveStageName() == 'foo')

        proddefObj = p.getProduct()
        _, kw = productClass._mock.popCall()
        kw = dict(kw)
        kw.pop('fromStream')

        configPath = self.workDir + '/foo/.rbuild/product-definition/rmakerc'
        self.assertEquals(p.getRmakeConfigPath(), configPath)
        mock.mockMethod(handle.facade.conary.updateCheckout)
        p.update()
        rbuildDir = p.getProductDefinitionDirectory()
        platformDir = p.getPlatformDefinitionDirectory()
        assert(platformDir == self.workDir + '/foo/.rbuild/platform-definition')
        handle.facade.conary.updateCheckout._mock.assertCalled(rbuildDir)

        proddefObj.getStages._mock.setDefaultReturn(
                                                [mock.MockObject(name='a'),
                                                 mock.MockObject(name='b'),
                                                 mock.MockObject(name='c')])
        stageNames = [x for x in p.iterStageNames()]
        self.assertEquals(stageNames, ['a', 'b', 'c'])

    def testUpdateError(self):
        productStore = mock.MockInstance(dirstore.CheckoutProductStore)
        productStore._mock.enableMethod('update')
        productStore._handle.facade.conary.updateCheckout._mock.setDefaultReturn(False)
        err = self.assertRaises(errors.RbuildError, productStore.update)
        assert(str(err) == "Failed to update product definition")

    def testProductDirectoryError(self):
        productStoreClass = mock.mockClass(dirstore.CheckoutProductStore)
        productStore = productStoreClass()
        productStore._mock.enable('_testProductDirectory')
        err = self.assertRaises(errors.RbuildError,
                                productStore._testProductDirectory,
                                self.workDir)
        assert(str(err) == "No product directory at %r" %self.workDir)


    def testGetEditedRecipeDicts(self):
        realListDir = os.listdir
        realExists = os.path.exists
        def mockListDir(path):
            if path.endswith('/qa'):
                return ['asdf' ]
            return realListDir(path)
        def mockExists(path):
            if path.endswith('CONARY'):
                return True
            if path.startswith('/PROD'):
                return True
            return realExists(path)

        self.mock(os, 'listdir', lambda *args: mockListDir(*args))
        self.mock(os.path, 'exists', lambda *args: mockExists(*args))
        productStore = mock.MockInstance(dirstore.CheckoutProductStore)
        productStore._mock.enableMethod('getEditedRecipeDicts')
        productStore.getRbuildConfigPath._mock.setReturn(
                                                self.workDir + '/rbuildrc')

        handle = self.getRbuildHandle(productStore=productStore)
        productStore._handle.facade.conary = mock.MockObject()
        stateObj = mock.MockObject()
        stateObj.getSourceState().getName._mock.setDefaultReturn('asdf:source')
        mock.mock(state, 'ConaryStateFromFile')
        state.ConaryStateFromFile._mock.setDefaultReturn(stateObj)

        productStore._handle.facade.conary.getNameForCheckout._mock.setDefaultReturn('asdf')
        productStore._handle.facade.conary.isGroupName._mock.setDefaultReturn(False)
        productStore.getActiveStageName._mock.setDefaultReturn(None)
        productStore.getStageDirectory._mock.setDefaultReturn('/PROD/qa')
        packageDict, groupDict = productStore.getEditedRecipeDicts('qa')
        assert packageDict == {'asdf' : '/PROD/qa/asdf/asdf.recipe'}
        assert groupDict == {}
        productStore.getActiveStageName._mock.setDefaultReturn('qa')
        packageDict, groupDict = productStore.getEditedRecipeDicts()
        assert packageDict == {'asdf' : '/PROD/qa/asdf/asdf.recipe'}
        assert groupDict == {}

        productStore._handle.facade.conary.getNameForCheckout._mock.setDefaultReturn('group-asdf')
        productStore._handle.facade.conary.isGroupName._mock.setDefaultReturn(True)
        stateObj.getSourceState().getName._mock.setDefaultReturn(
                                                          'group-asdf:source')
        packageDict, groupDict = productStore.getEditedRecipeDicts('qa')

        assert packageDict == {}
        assert groupDict == {'group-asdf' : '/PROD/qa/asdf/group-asdf.recipe'}

    def testStatusStore(self):
        productStore = mock.MockInstance(dirstore.CheckoutProductStore)
        productStore._mock.set(statusStore=None)
        productStore._mock.enableMethod('setStatus')
        productStore._mock.enableMethod('getStatus')
        productStore._mock.enableMethod('_getStatusStore')
        productStore._mock.enableMethod('getPackageJobId')
        productStore._mock.enableMethod('getGroupJobId')
        productStore._mock.enableMethod('getImageJobId')
        productStore._mock.enableMethod('setPackageJobId')
        productStore._mock.enableMethod('setGroupJobId')
        productStore._mock.enableMethod('setImageJobId')
        productStore.iterStageNames._mock.setDefaultReturn(['teststage'])
        productStore.getActiveStageName._mock.setDefaultReturn('teststage')
        productStore._mock.enable('_baseDirectory')
        productStore._baseDirectory = self.workDir

        assert(productStore.getGroupJobId() is None)
        assert(productStore.getImageJobId() is None)
        assert(productStore.getPackageJobId() is None)
        productStore.setGroupJobId(10)
        assert(productStore.getGroupJobId() is 10)
        productStore.setImageJobId(15)
        assert(productStore.getImageJobId() is 15)
        productStore.setPackageJobId(20)
        assert(productStore.getGroupJobId() is 10)
        assert(productStore.getImageJobId() is 15)
        assert(productStore.getPackageJobId() is 20)
        # key 'foo' is not defined
        self.assertRaises(KeyError, productStore.setStatus, 'foo', 'asdf')

    def testCheckoutPlatform(self):
        productStore = mock.MockInstance(dirstore.CheckoutProductStore)
        productStore._handle.product.getProductDefinitionLabel._mock.setDefaultReturn('localhost@rpl:2')
        productStore.getPlatformDefinitionDirectory._mock.setDefaultReturn(self.workDir)
        productStore._mock.enableMethod('checkoutPlatform')
        productStore.checkoutPlatform()
        productStore._handle.facade.conary.checkout._mock.assertCalled(
                                                'platform-definition', 
                                                'localhost@rpl:2',
                                                targetDir=self.workDir)

    def testGetPlatformAutoLoadRecipes(self):
        productStore = mock.MockInstance(dirstore.CheckoutProductStore)
        productStore._mock.enableMethod('getPlatformAutoLoadRecipes')
        productStore._handle.product.getPlatformAutoLoadRecipes._mock.setReturn([])
        alr = productStore.getPlatformAutoLoadRecipes()
        assert(alr == [])

        pd = proddef.PlatformDefinition()
        alRecipes = [('foo', 'foo.rpath.com@foo:1'),
            ('bar', 'bar.rpath.com@bar:1')]
        for troveName, label in alRecipes:
            pd.addAutoLoadRecipe(troveName, label)

        productStore._handle.product.getPlatformAutoLoadRecipes._mock.setReturn(pd.getAutoLoadRecipes())
        alr = productStore.getPlatformAutoLoadRecipes()
        assert(alr == ['foo=foo.rpath.com@foo:1', 
                       'bar=bar.rpath.com@bar:1'])

    def testGetStageDirectory(self):
        productStore = mock.MockInstance(dirstore.CheckoutProductStore)
        productStore._mock.enableMethod('getStageDirectory')
        mock.mock(os.path, 'exists')
        os.path.exists._mock.setReturn(False, self.workDir + '/foo')
        productStore._mock.set(_baseDirectory=self.workDir)
        err = self.assertRaises(errors.RbuildError,
                                 productStore.getStageDirectory, 'foo')
        assert(str(err) == "Stage directory for 'foo' does not exist")
        os.path.exists._mock.setReturn(True, self.workDir + '/foo')
        workDir = productStore.getStageDirectory('foo')
        assert(workDir == self.workDir + '/foo')
        productStore.getActiveStageName._mock.setReturn(None)
        workDir = productStore.getStageDirectory()
        assert(workDir is None)
        productStore.getActiveStageName._mock.assertCalled()

    def testGetCheckoutDirectory(self):
        productStore = mock.MockInstance(dirstore.CheckoutProductStore)
        productStore._mock.enableMethod('getCheckoutDirectory')
        productStore.getStageDirectory._mock.setDefaultReturn('/PROD////qa')
        self.assertEquals(productStore.getCheckoutDirectory('foo'),
                          '/PROD/qa/foo')

    def testGetPackagePath(self):
        realListDir = os.listdir
        realExists = os.path.exists
        def mockListDir(path):
            if path.endswith('/qa'):
                return ['asdf' ]
            return realListDir(path)
        def mockExists(path):
            if path.endswith('CONARY'):
                return True
            if path.startswith('/PROD'):
                return True
            return realExists(path)

        self.mock(os, 'listdir', lambda *args: mockListDir(*args))
        self.mock(os.path, 'exists', lambda *args: mockExists(*args))

        productStore = mock.MockInstance(dirstore.CheckoutProductStore)
        productStore._mock.enableMethod('getPackagePath')
        productStore.getStageDirectory._mock.setDefaultReturn('/PROD/qa')

        handle = self.getRbuildHandle(productStore=productStore)
        productStore._handle.facade.conary = mock.MockObject()
        stateObj = mock.MockObject()
        stateObj.getSourceState().getName._mock.setDefaultReturn('asdf:source')
        mock.mock(state, 'ConaryStateFromFile')
        state.ConaryStateFromFile._mock.setDefaultReturn(stateObj)

        productStore._handle.facade.conary.getNameForCheckout._mock.setDefaultReturn('asdf')
        productStore._handle.facade.conary.isGroupName._mock.setDefaultReturn(False)

        packagePath = productStore.getPackagePath('asdf')
        assert(packagePath == '/PROD/qa/asdf')
        packagePath = productStore.getPackagePath('blah')
        assert(packagePath is None)

    def testGetConfigData(self):
        productStore = mock.MockInstance(dirstore.CheckoutProductStore)
        productStore._mock.enable('_baseDirectory')
        productStore._baseDirectory = self.workDir
        productStore._mock.enableMethod('getRbuildConfigData')
        productStore._mock.enableMethod('getRbuildConfigPath')
        productStore._mock.enableMethod('getRmakeConfigData')
        productStore._mock.enableMethod('getRmakeConfigPath')
        productStore.getProductDefinitionDirectory._mock.setDefaultReturn(
            self.workDir)
        os.chdir(self.workDir)
        util.mkdirChain('.rbuild')
        self.writeFile('.rbuild/rbuildrc', 'rbuildrcContents\n')
        self.writeFile('rmakerc', 'rmakercContents\n')
        self.assertEquals(productStore.getRbuildConfigData(),
                          'rbuildrcContents\n')
        self.assertEquals(productStore.getRmakeConfigData(),
                          'rmakercContents\n')

    def testGetProductVersion(self):
        productStore = mock.MockInstance(dirstore.CheckoutProductStore)
        productStore._mock.enableMethod('getProductVersion')
        product = mock.MockObject()
        product.getProductVersion._mock.setDefaultReturn('42.42')
        productStore.getProduct._mock.setDefaultReturn(product)
        self.assertEquals(productStore.getProductVersion(), '42.42')

