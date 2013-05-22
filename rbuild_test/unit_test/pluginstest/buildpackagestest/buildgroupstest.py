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



from rbuild import errors
from rbuild_test import rbuildhelp
from testutils import mock

class BuildGroupsTest(rbuildhelp.RbuildHelper):
    def testCommandParsing(self):
        handle = self.getRbuildHandle()
        handle.Build.registerCommands()
        handle.Build.initialize()
        handle.BuildGroups.initialize()
        cmd = handle.Commands.getCommandClass('build')()
        mock.mockMethod(handle.BuildGroups.buildAllGroups, 1)
        mock.mockMethod(handle.Build.watchAndCommitJob)
        cmd.runCommand(handle, {}, ['rbuild', 'build', 'groups'])
        handle.BuildGroups.buildAllGroups._mock.assertCalled()
        handle.Build.watchAndCommitJob._mock.assertCalled(1, None)

        mock.mockMethod(handle.BuildGroups.buildGroups, 1)
        mock.mockMethod(handle.Build.watchJob)
        cmd.runCommand(handle, {'no-commit': True}, 
                       ['rbuild', 'build', 'groups', 'group-foo'])
        handle.BuildGroups.buildGroups._mock.assertCalled(['group-foo'])
        handle.Build.watchJob._mock.assertCalled(1)
        cmd.runCommand(handle, {'no-watch': True},
                       ['rbuild', 'build', 'groups', 'group-foo'])
        handle.Build.watchJob._mock.assertNotCalled()

        handle.Build.watchAndCommitJob._mock.setDefaultReturn(False)
        self.assertRaises(errors.PluginError,
            cmd.runCommand, handle, {}, ['rbuild', 'build', 'groups'])

    def testBuildAllGroups(self):
        handle = self.getRbuildHandle()
        from rbuild_plugins.build import groups
        mock.mock(groups, 'createRmakeJobForAllGroups', 'group-foo')
        mock.mockMethod(handle.facade.rmake.buildJob)
        mock.mockMethod(handle.Build.warnIfOldProductDefinition)
        handle.productStore = mock.MockObject()
        handle.BuildGroups.buildAllGroups()
        groups.createRmakeJobForAllGroups._mock.assertCalled(handle)
        handle.facade.rmake.buildJob._mock.assertCalled('group-foo')
        handle.Build.warnIfOldProductDefinition._mock.assertCalled(
            'building all groups')

    def testBuildGroups(self):
        handle = self.getRbuildHandle()
        from rbuild_plugins.build import groups
        mock.mock(groups, 'createRmakeJobForGroups', 'group-foo')
        mock.mockMethod(handle.facade.rmake.buildJob)
        mock.mockMethod(handle.Build.warnIfOldProductDefinition)
        handle.productStore = mock.MockObject()
        handle.BuildGroups.buildGroups(['pkg1'])
        groups.createRmakeJobForGroups._mock.assertCalled(handle,
                                                                 ['pkg1'])
        handle.facade.rmake.buildJob._mock.assertCalled('group-foo')
        handle.Build.warnIfOldProductDefinition._mock.assertCalled(
            'building groups')

    def testCommand(self):
        self.checkRbuild('build groups --no-watch --no-commit',
            'rbuild_plugins.buildgroups.BuildGroupsCommand.runCommand',
            [None, None, {'no-watch' : True, 'no-commit' : True}, 
            ['build', 'groups']])


