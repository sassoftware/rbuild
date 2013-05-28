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

from conary.lib import log

from rbuild import errors

class BuildPackagesTest(rbuildhelp.RbuildHelper):
    def testCreateRmakeJobForAllPackages(self):
        handle = self.getRbuildHandle()
        from rbuild_plugins.build import packages
        handle.productStore = mock.MockObject()
        handle.productStore.getGroupFlavors._mock.setReturn([])
        packageRecipes = {'foo' : self.workDir + '/foo/foo.recipe'}
        handle.productStore.getEditedRecipeDicts._mock.setReturn(
                                                        (packageRecipes, {}))
        mock.mock(packages, '_addInEditedPackages', 'return')
        rc = packages.createRmakeJobForAllPackages(handle)
        assert(rc == 'return')
        handle.productStore.getEditedRecipeDicts._mock.setReturn(
                                                        ({}, {}))
        err = self.assertRaises(errors.PluginError,
                                packages.createRmakeJobForAllPackages, handle)
        assert(str(err) == ('no packages are currently being edited'
                            ' - nothing to build'))

    def testCreateRmakeJobForPackages(self):
        handle = self.getRbuildHandle()
        from rbuild_plugins.build import packages
        handle.productStore = mock.MockObject()
        handle.productStore.getGroupFlavors._mock.setReturn([])
        packageRecipes = {'foo' : self.workDir + '/foo/foo.recipe', 
                          'bar' : self.workDir + '/bar/bar.recipe'}
        handle.productStore.getEditedRecipeDicts._mock.setReturn(
                                                        (packageRecipes, {}))
        mock.mock(packages, '_addInEditedPackages', 'return')
        rc = packages.createRmakeJobForPackages(handle, ['foo'])
        assert(rc == 'return')
        packages._addInEditedPackages._mock.assertCalled(handle, None,
                                    {'foo' : self.workDir + '/foo/foo.recipe'})

        err = self.assertRaises(errors.PluginError,
                                packages.createRmakeJobForPackages, handle,
                                ['foo', 'zzz', 'bam'])
        assert(str(err) == ('the following packages were not found: bam, zzz'))

    def testCreateRmakeJobForExactPackages(self):
        handle = self.getRbuildHandle()
        from rbuild_plugins.build import packages
        handle.productStore = mock.MockObject()
        handle.productStore.getGroupFlavors._mock.setReturn([(None, 'a')])
        mock.mockMethod(handle.facade.rmake._getRmakeContexts)
        handle.facade.rmake._getRmakeContexts._mock.setReturn({'a': 'ACTX'})
        packageRecipes = {'foo': self.workDir + '/foo/foo.recipe'}
        groupRecipes = {
                'group-baz': self.workDir + '/group-baz/group-baz.recipe'}
        handle.productStore.getEditedRecipeDicts._mock.setReturn(
            (packageRecipes, groupRecipes))
        mock.mockMethod(handle.facade.rmake.createBuildJobForStage)

        # normal
        packages.createRmakeJobForPackages(handle,
                ['foo', 'bar', 'group-baz'], False)

        handle.facade.rmake.createBuildJobForStage._mock.assertCalled(
            [self.workDir + '/foo/foo.recipe{ACTX}', 'bar{ACTX}',
                self.workDir + '/group-baz/group-baz.recipe{ACTX}'],
            recurse=False, rebuild=False, useLocal=True)

        # no group flavors
        handle.productStore.getGroupFlavors._mock.setReturn([])
        err = self.assertRaises(errors.PluginError,
            packages.createRmakeJobForPackages, handle, ['foo', 'bar'], False)
        self.failUnlessEqual(str(err), "no image flavors defined; don't know "
            "what to build")


    def testAddInEditedPackages(self):
        handle = self.getRbuildHandle()
        from rbuild_plugins.build import packages
        replacementRecipes = ['foo/foo.recipe']
        newRecipes = {}
        mock.mock(packages, '_removePackagesWithEditedReplacements',
                  (replacementRecipes, newRecipes))
        mock.mockMethod(handle.facade.rmake.createBuildJobForStage)
        mock.mock(handle, 'ui')
        handle.facade.rmake.createBuildJobForStage._mock.setReturn('recipeJob',
                                                            replacementRecipes)
        mock.mock(handle.facade.rmake, 'overlayJob')
        handle.facade.rmake.overlayJob._mock.setReturn('mainJob+recipeJob',
                                                       'mainJob', 'recipeJob')
        newJob = packages._addInEditedPackages(handle, 'mainJob', 
                                               replacementRecipes)
        self.assertEquals(newJob, 'mainJob+recipeJob')


        # test 2: pass in new recipes
        newRecipes = {'bar' : self.workDir + '/bar.recipe'}
        packages._removePackagesWithEditedReplacements._mock.setDefaultReturn(
                                      (list(replacementRecipes), newRecipes))
        mock.mockMethod(handle.facade.rmake._getRmakeContexts,
                        {'is: x86' : 'x86',
                         'is: x86_64' : 'x86_64' })
        allRecipes = list(replacementRecipes)
        allRecipes.extend([self.workDir + '/bar.recipe{x86}',
                           self.workDir + '/bar.recipe{x86_64}'])
        handle.facade.rmake.createBuildJobForStage._mock.setReturn('recipeJob2',
                                                                   allRecipes)
        handle.facade.rmake.overlayJob._mock.setReturn('mainJob+recipeJob2',
                                                       'mainJob', 'recipeJob2')
        newJob = packages._addInEditedPackages(handle, 'mainJob',
                                               list(replacementRecipes))
        self.assertEquals(newJob, 'mainJob+recipeJob2')
        warningTxt = ('the following edited packages were not in any groups'
                      ' or have not been committed yet - building with default'
                      ' flavors: bar')
        handle.ui.warning._mock.assertCalled(warningTxt)

    def testRemovePackagesWithEditedReplacements(self):
        self.getRbuildHandle() # prime plugins
        from rbuild_plugins.build import packages
        packageRecipes = {'bar' : self.workDir + '/bar.recipe',
                          'foo' : self.workDir + '/foo.recipe'}
        mainJob = mock.MockObject()
        mainJob.iterTroveList(withContexts=True)._mock.setList(
                            [('foo:source', 'ver', 'flavor', 'context'),
                             ('foo:source', 'ver', 'flavor2', 'context2'),
                             ('group-dist:source', 'ver', 'flavor', 'context2'),
                             ('bam:source', 'ver2', 'flavor2', 'context2')])
        item = packages._removePackagesWithEditedReplacements(mainJob,
                                                              packageRecipes)
        assert(item == ([ self.workDir + '/foo.recipe[flavor]{context}', 
                          self.workDir + '/foo.recipe[flavor2]{context2}'],
                        {'bar': self.workDir + '/bar.recipe'}))
        mainJob.removeTrove._mock.assertCalled('foo:source', 
                                               'ver', 'flavor', 'context')
        mainJob.removeTrove._mock.assertCalled('foo:source', 
                                               'ver', 'flavor2', 'context2')
        mainJob.removeTrove._mock.assertCalled('group-dist:source', 
                                               'ver', 'flavor', 'context2')

        item = packages._removePackagesWithEditedReplacements(None,
                                                              packageRecipes)
        assert(item == ([], packageRecipes))




