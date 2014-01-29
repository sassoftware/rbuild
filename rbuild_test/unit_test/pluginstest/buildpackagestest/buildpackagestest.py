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


class BuildPackagesTest(rbuildhelp.RbuildHelper):
    def testCommandParsing(self):
        handle = self.getRbuildHandle()
        handle.Build.registerCommands()
        handle.Build.initialize()
        handle.BuildPackages.initialize()
        cmd = handle.Commands.getCommandClass('build')()
        mock.mockMethod(handle.BuildPackages.buildAllPackages, 1)
        mock.mockMethod(handle.Build.watchAndCommitJob)
        mock.mockMethod(handle.BuildPackages.refreshAllPackages, 1)

        err = self.assertRaises(errors.PluginError, cmd.runCommand, handle, {},
                                ['rbuild', 'build', 'packages'])
        self.assertIn('rbuild init', str(err))

        mock.mock(handle, 'productStore')
        handle.productStore._mock.set(_currentStage=None)

        err = self.assertRaises(errors.PluginError, cmd.runCommand, handle, {},
                                ['rbuild', 'build', 'packages'])
        self.assertIn('valid stage', str(err))

        handle.productStore._mock.set(_currentStage='stage')

        cmd.runCommand(handle, {}, ['rbuild', 'build', 'packages'])
        handle.BuildPackages.buildAllPackages._mock.assertCalled()
        handle.Build.watchAndCommitJob._mock.assertCalled(1, None)
        handle.BuildPackages.refreshAllPackages._mock.assertNotCalled()

        cmd.runCommand(handle, {}, ['rbuild', 'build', 'package'])
        handle.BuildPackages.buildAllPackages._mock.assertCalled()
        handle.Build.watchAndCommitJob._mock.assertCalled(1, None)
        handle.BuildPackages.refreshAllPackages._mock.assertNotCalled()

        cmd.runCommand(handle, {'message': 'message from unit tests'},
                       ['rbuild', 'build', 'packages'])
        handle.BuildPackages.buildAllPackages._mock.assertCalled()
        handle.Build.watchAndCommitJob._mock.assertCalled(1,
            'message from unit tests')
        handle.BuildPackages.refreshAllPackages._mock.assertNotCalled()

        mock.mockMethod(handle.BuildPackages.buildPackages, 1)
        mock.mockMethod(handle.Build.watchJob)
        mock.mockMethod(handle.BuildPackages.refreshPackages, 1)
        cmd.runCommand(handle, {'no-commit': True},
                       ['rbuild', 'build', 'packages', 'foo'])
        handle.BuildPackages.buildPackages._mock.assertCalled(['foo'], False)

        handle.Build.watchJob._mock.assertCalled(1)
        handle.BuildPackages.refreshPackages._mock.assertNotCalled()
        handle.BuildPackages.refreshAllPackages._mock.assertNotCalled()
        cmd.runCommand(handle, {'no-watch': True},
                       ['rbuild', 'build', 'packages', 'foo'])
        handle.Build.watchJob._mock.assertNotCalled()
        handle.BuildPackages.refreshPackages._mock.assertNotCalled()
        handle.BuildPackages.refreshAllPackages._mock.assertNotCalled()

        cmd.runCommand(handle, {'refresh': True},
                       ['rbuild', 'build', 'packages'])
        handle.BuildPackages.refreshAllPackages._mock.assertCalled()
        handle.BuildPackages.refreshPackages._mock.assertNotCalled()

        cmd.runCommand(handle, {'refresh': True},
                       ['rbuild', 'build', 'packages', 'foo'])
        handle.BuildPackages.refreshAllPackages._mock.assertNotCalled()
        handle.BuildPackages.refreshPackages._mock.assertCalled(['foo'])

        handle.Build.watchAndCommitJob._mock.setDefaultReturn(False)
        self.assertRaises(errors.PluginError,
            cmd.runCommand, handle, {}, ['rbuild', 'build', 'packages'])

    def testBuildAllPackages(self):
        handle = self.getRbuildHandle()
        from rbuild_plugins.build import packages
        mock.mock(packages, 'createRmakeJobForAllPackages', 'foo')
        mock.mockMethod(handle.facade.rmake.buildJob)
        mock.mockMethod(handle.Build.warnIfOldProductDefinition)
        handle.productStore = mock.MockObject()
        handle.BuildPackages.buildAllPackages()
        packages.createRmakeJobForAllPackages._mock.assertCalled(handle)
        handle.facade.rmake.buildJob._mock.assertCalled('foo')
        handle.Build.warnIfOldProductDefinition._mock.assertCalled(
            'building all packages')

    def testBuildPackages(self):
        handle = self.getRbuildHandle()
        from rbuild_plugins.build import packages
        mock.mock(packages, 'createRmakeJobForPackages', 'foo')
        mock.mockMethod(handle.facade.rmake.buildJob)
        mock.mockMethod(handle.Build.warnIfOldProductDefinition)
        handle.productStore = mock.MockObject()
        handle.BuildPackages.buildPackages(['pkg1'])
        packages.createRmakeJobForPackages._mock.assertCalled(handle,
            ['pkg1'], True)
        handle.facade.rmake.buildJob._mock.assertCalled('foo')
        handle.Build.warnIfOldProductDefinition._mock.assertCalled(
            'building packages')

    def testBuildPackagesRefresh(self):
        handle = self.getRbuildHandle()
        from rbuild_plugins.build import refresh
        mock.mock(refresh, 'refreshPackages', 'foo')
        handle.BuildPackages.refreshPackages(['pkg1'])
        refresh.refreshPackages._mock.assertCalled(handle, ['pkg1'])

    def testBuildAllPackagesRefresh(self):
        handle = self.getRbuildHandle()
        from rbuild_plugins.build import refresh
        mock.mock(refresh, 'refreshAllPackages', 'foo')
        handle.BuildPackages.refreshAllPackages()
        refresh.refreshAllPackages._mock.assertCalled(handle)

    def testBuildPackages2(self):
        handle = self.getRbuildHandle()
        from rbuild_plugins.build import packages
        mock.mock(packages, 'createRmakeJobForPackages', 'foo')
        mock.mockMethod(handle.facade.rmake.buildJob)
        mock.mockMethod(handle.Build.warnIfOldProductDefinition)
        handle.productStore = mock.MockObject()
        handle.BuildPackages.buildPackages(['pkg2', 'pkg3'], recurse=False)
        packages.createRmakeJobForPackages._mock.assertCalled(handle,
            ['pkg2', 'pkg3'], False)
        handle.facade.rmake.buildJob._mock.assertCalled('foo')

    def testWatchAndCommitJob(self):
        handle = self.getRbuildHandle()
        mock.mockMethod(handle.facade.rmake.watchAndCommitJob)
        handle.Build.watchAndCommitJob(1, '')
        handle.facade.rmake.watchAndCommitJob._mock.assertCalled(1, '')

    def testWatchJob(self):
        handle = self.getRbuildHandle()
        mock.mockMethod(handle.facade.rmake.watchJob)
        handle.Build.watchJob(1)
        handle.facade.rmake.watchJob._mock.assertCalled(1)

    def testCommand(self):
        self.checkRbuild('build packages --no-watch --no-commit --recurse',
            'rbuild_plugins.buildpackages.BuildPackagesCommand.runCommand',
            [None, None, {'no-watch': True, 'no-commit': True,
                          'recurse': True},
             ['build', 'packages']])


