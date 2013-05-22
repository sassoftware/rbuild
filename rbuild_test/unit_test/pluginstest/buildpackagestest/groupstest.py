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

from rbuild import errors

class BuildGroupsTest(rbuildhelp.RbuildHelper):

    def testGetJobBasedOnProductGroups(self):
        handle = self.getRbuildHandle()
        self.rbuildCfg.serverUrl = None
        from rbuild_plugins.build import groups
        handle.productStore = mock.MockObject()
        handle.product = mock.MockObject()

        groupFlavors = [('group-dist', 'is: x86'),
                        ('group-dist', 'is: x86_64')]
        handle.productStore.getGroupFlavors._mock.setReturn(groupFlavors)
        handle.productStore.getRmakeConfigPath._mock.setReturn(
                                                self.workDir + '/rmakerc')
        label = 'localhost@rpl:linux'
        handle.productStore.getActiveStageLabel._mock.setReturn(label)
        handle.product.getLabelForStage._mock.setReturn(label)
        handle.product.getBaseFlavor._mock.setReturn('')
        mock.mockMethod(handle.facade.conary._findTroves)
        groupSpec = ('group-dist:source', None, None)
        groupTup = self.makeTroveTuple('group-dist:source=@rpl:linux/1.0-1')
        handle.facade.conary._findTroves._mock.setReturn(
                                                    {groupSpec : [groupTup]},
                                                    [groupSpec],
                                                    label, allowMissing=True)
        groupsToBuild = ['group-dist{x86}', 'group-dist{x86_64}']
        mock.mockMethod(handle.facade.rmake.createBuildJobForStage)
        handle.facade.rmake.createBuildJobForStage._mock.setReturn('r1',
                                                groupsToBuild, recurse=True)

        # test1
        job = groups._getJobBasedOnProductGroups(handle, {}, recurse=True)
        assert(job == 'r1')

        # test2: test to see what it does when there are no groups.
        handle.facade.conary._findTroves._mock.setReturn({},
                                                    [groupSpec],
                                                    label, allowMissing=True)
        job = groups._getJobBasedOnProductGroups(handle, {}, recurse=True)
        assert(job is None)

        # test3: when there is a replacement group recipe, we should use
        # the one on disk and not search the repository for it.
        groupRecipe = self.workDir + '/group-dist.recipe'
        groupsToBuild = [ groupRecipe + '{x86}', groupRecipe + '{x86_64}']
        handle.facade.rmake.createBuildJobForStage._mock.setReturn('r2',
                                                groupsToBuild, recurse=True)
        handle.facade.conary._findTroves._mock.setReturn({},
                                                    [], label,
                                                    allowMissing=True)
        job = groups._getJobBasedOnProductGroups(handle, 
                                                   {'group-dist' : groupRecipe},
                                                   recurse=True)
        assert(job == 'r2')
        # test 3 -  no groups.
        handle.productStore.getGroupFlavors._mock.setReturn([])
        job = groups._getJobBasedOnProductGroups(handle, {}, recurse=True)
        assert(job is None)

    def testCreateRmakeJobForGroups(self):
        handle = self.getRbuildHandle()
        from rbuild_plugins.build import groups
        mock.mock(groups, '_createRmakeJobForGroups', 1)
        assert(groups.createRmakeJobForGroups(handle, ['foo']) == 1)
        groups._createRmakeJobForGroups._mock.assertCalled(handle, ['foo'])
        assert(groups.createRmakeJobForAllGroups(handle) == 1)
        groups._createRmakeJobForGroups._mock.assertCalled(handle)

    def test_createRmakeJobForGroups(self):
        handle = self.getRbuildHandle()
        from rbuild_plugins.build import groups
        handle.productStore = mock.MockObject()
        handle.productStore.getEditedRecipeDicts._mock.setReturn(({}, {}))
        err = self.assertRaises(errors.PluginError,
                                groups._createRmakeJobForGroups, handle)
        self.failUnlessEqual(err.msg, 'no groups are currently being '
            'edited - nothing to build')
        err = self.assertRaises(errors.PluginError,
                                groups._createRmakeJobForGroups, handle,
                                ['group-foo'])
        assert(str(err) == 'the following groups were not found: group-foo')
        mock.mock(groups, '_getJobBasedOnProductGroups', 'mainJob')
        groupRecipes = {'group-dist':self.workDir + '/group-dist.recipe'}
        handle.productStore.getEditedRecipeDicts._mock.setReturn(
                    ({}, groupRecipes))
        rc = groups._createRmakeJobForGroups(handle)
        assert(rc == 'mainJob')
        groups._getJobBasedOnProductGroups._mock.assertCalled(handle,
                                                              groupRecipes)
        rc = groups._createRmakeJobForGroups(handle, ['group-dist'])
        assert(rc == 'mainJob')
        groups._getJobBasedOnProductGroups._mock.assertCalled(handle,
                                                              groupRecipes)
        groups._getJobBasedOnProductGroups._mock.setDefaultReturn(None)
        err = self.assertRaises(errors.PluginError,
                                groups._createRmakeJobForGroups, handle)
        assert(str(err) == 'No groups found to build')

