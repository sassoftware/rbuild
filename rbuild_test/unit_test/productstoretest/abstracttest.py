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
from rbuild.productstore import abstract

class AbstractProductTest(rbuildhelp.RbuildHelper):
    def testCore(self):
        pd = proddef.ProductDefinition()
        pd.setConaryRepositoryHostname('localhost')
        pd.setConaryNamespace('rpl')
        pd.setProductShortname('a')
        pd.setProductVersion('1')
        pd.addStage('foo', '')
        pd.addStage('bar', '-bar')

        productClass = mock.MockObject(stableReturnValues=True)
        productClass._mock.setReturn(pd)
        self.mock(proddef, 'ProductDefinition', productClass)

        handle = self.getRbuildHandle()
        p = abstract.ProductStore(handle)

        proddefObj = p.getProduct()
        _, kw = productClass._mock.popCall()
        kw = dict(kw)
        self.assertEquals(kw, {}) # no fromStream=

        # get trivial errors out of the way first
        self.assertRaises(errors.IncompleteInterfaceError, p.getStatus, 'asdf')
        self.assertRaises(errors.IncompleteInterfaceError, p.getPackageJobId)
        self.assertRaises(errors.IncompleteInterfaceError, p.getGroupJobId)
        self.assertRaises(errors.IncompleteInterfaceError, p.getImageJobId)
        self.assertRaises(errors.IncompleteInterfaceError, p.setPackageJobId, 1)
        self.assertRaises(errors.IncompleteInterfaceError, p.setGroupJobId, 1)
        self.assertRaises(errors.IncompleteInterfaceError, p.setImageJobId, 1)
        self.assertRaises(errors.IncompleteInterfaceError, p.getRbuildConfigData)
        self.assertRaises(errors.RbuildError, p.getRbuildConfigPath)
        self.assertRaises(errors.IncompleteInterfaceError, p.getRmakeConfigData)
        self.assertRaises(errors.RbuildError, p.getRmakeConfigPath)

        handle.product = None
        p.update()
        self.assertEquals(handle.product, proddefObj)

        self.assertEquals([x for x in p.iterStageNames()], ['foo', 'bar'])

        self.assertEquals(p.getNextStageName('foo'), 'bar')
        self.assertEquals(p.getNextStageName('bar'), None)

        self.assertRaises(errors.RbuildError, p.checkStageIsValid, 'fdsa')

        p._currentStage = None
        self.assertRaises(errors.RbuildError, p.getActiveStageName)
        mock.mockMethod(p.checkStageIsValid)
        p.setActiveStageName('foo')
        p.checkStageIsValid._mock.assertCalled('foo')
        self.assertEquals(p.getActiveStageName(), 'foo')

        self.assertEquals(p.getActiveStageLabel(), 'localhost@rpl:a-1')

    def testGetGroupFlavors(self):
        handle = self.getRbuildHandle()
        productStore = abstract.ProductStore(handle)
        product = proddef.ProductDefinition()
        product.setBaseFlavor('ssl,readline')
        handle.product = product
        mock.mockMethod(productStore.getProduct)
        productStore.getProduct._mock.setDefaultReturn(product)
        # First, make sure that zero images defined is an error RBLD-171
        self.assertRaises(errors.MissingImageDefinitionError,
            productStore.getGroupFlavors)

        # Now, test that the right flavor sets are found
        product.addBuildDefinition(imageGroup='group-foo', 
                                   flavor='is: x86')
        product.addBuildDefinition(imageGroup='group-bar', 
                                   flavor='is: x86_64')
        results = productStore.getGroupFlavors()
        # These flavors are too simplistic to work in practice! RBLD-172
        x86Flavor = 'readline,ssl is: x86'
        x8664Flavor = 'readline,ssl is: x86_64'
        assert(results == [ ('group-foo', x86Flavor), 
                            ('group-bar', x8664Flavor)])


    def testGetBuildDefinitionGroupToBuild(self):
        handle = self.getRbuildHandle()
        productStore = abstract.ProductStore(handle)
        product = proddef.ProductDefinition()
        handle.product = product

        mock.mockMethod(productStore.getSourceGroupMatch)
        productStore.getSourceGroupMatch._mock.setDefaultReturn(
            'group-source-match')

        product.addBuildDefinition(imageGroup='group-foo',
                                   sourceGroup='group-foo-source',
                                   flavor='is: x86')
        bd = product.buildDefinition[0]
        results = productStore.getBuildDefinitionGroupToBuild(bd)
        self.assertEquals(results, 'group-foo-source')
                                           
        product.addBuildDefinition(imageGroup='group-bar',
                                   sourceGroup='group-bar-source',
                                   flavor='is: x86')
        bd = product.buildDefinition[1]
        results = productStore.getBuildDefinitionGroupToBuild(bd)
        self.assertEquals(results, 'group-bar-source')

        product.setSourceGroup('group-toplevel-source')

        product.addBuildDefinition(imageGroup='group-bar',
                                   flavor='is: x86')
        bd = product.buildDefinition[2]
        results = productStore.getBuildDefinitionGroupToBuild(bd)
        self.assertEquals(results, 'group-toplevel-source')

        product.addBuildDefinition(imageGroup='group-bar',
                                   sourceGroup='group-bar-source',
                                   flavor='is: x86')
        bd = product.buildDefinition[3]
        results = productStore.getBuildDefinitionGroupToBuild(bd)
        self.assertEquals(results, 'group-bar-source')

        product.setSourceGroup(None)
        product.addBuildDefinition(imageGroup='group-bar',
                                   flavor='is: x86')
        bd = product.buildDefinition[4]
        results = productStore.getBuildDefinitionGroupToBuild(bd)
        self.assertEquals(results, 'group-source-match')

    def testGetSourceGroupMatch(self):
        handle = self.getRbuildHandle()
        productStore = abstract.ProductStore(handle)
        product = proddef.ProductDefinition()
        product.setBaseFlavor('ssl,readline')
        handle.product = product

        product.addBuildDefinition(imageGroup = 'group-foo',
                                   sourceGroup = 'group-foo-source',
                                   flavor = 'is: x86')
        product.addBuildDefinition(imageGroup = 'group-foo',
                                   flavor = 'is: x86')
        
        bd = product.buildDefinition[1]
        results = productStore.getSourceGroupMatch(bd)
        self.assertEquals(results, 'group-foo-source')

        product.addBuildDefinition(flavor = 'is: x86')
        bd = product.buildDefinition[2]
        results = productStore.getSourceGroupMatch(bd)
        self.assertEquals(results, None)


    def testGetBuildsWithFullFlavors(self):
        handle = self.getRbuildHandle()
        productStore = abstract.ProductStore(handle)
        product = mock.MockInstance(proddef.ProductDefinition)
        handle.product = product

        build1 = mock.MockObject()
        build1.getBuildBaseFlavor._mock.setDefaultReturn('is: x86')
        build2 = mock.MockObject()
        build2.getBuildBaseFlavor._mock.setDefaultReturn('is: x86_64')
        
        product.getBuildsForStage._mock.setDefaultReturn([build1, build2])
        product.getBaseFlavor._mock.setDefaultReturn('qt')

        r = productStore.getBuildsWithFullFlavors('devel')
        self.assertEquals(r,
            [(build1, 'qt is: x86'), (build2, 'qt is: x86_64')])

        product.getBuildsForStage._mock.setDefaultReturn([])
        self.assertRaises(errors.MissingImageDefinitionError,
            productStore.getBuildsWithFullFlavors, 'devel')

    def testGetPlatformAutoLoadRecipes(self):
        pd = proddef.ProductDefinition()

        productStore = mock.MockInstance(abstract.ProductStore)
        productStore._mock.enableMethod('getPlatformAutoLoadRecipes')
        productStore._handle._mock.set(product=pd)
        alr = productStore.getPlatformAutoLoadRecipes()
        assert(alr == [])

        alRecipes = [('foo', 'foo.rpath.com@foo:1'),
            ('bar', 'bar.rpath.com@bar:1')]
        for troveName, label in alRecipes:
            pd.addPlatformAutoLoadRecipe(troveName, label)

        alr = productStore.getPlatformAutoLoadRecipes()
        assert(alr == ['foo=foo.rpath.com@foo:1',
                       'bar=bar.rpath.com@bar:1'])
