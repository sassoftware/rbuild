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
from testutils import mock

from rbuild_test import rbuildhelp


class ListBranchesTest(rbuildhelp.RbuildHelper):
    def testCommandParsing(self):
        handle = self.getRbuildHandle()
        handle.List.registerCommands()
        handle.Branches.initialize()
        handle.List.initialize()
        cmd = handle.Commands.getCommandClass('list')()

        mock.mockMethod(handle.Branches.list)

        err = self.assertRaises(
            errors.ParseError,
            cmd.runCommand,
            handle,
            {},
            ['rbuild', 'list', 'branches']
            )

        cmd.runCommand(handle, {}, ['rbuild', 'list', 'branches', 'foo'])
        handle.Branches.list._mock.assertCalled('foo')

    def testCommand(self):
        self.getRbuildHandle()
        self.checkRbuild('list branches',
            'rbuild_plugins.branches.ListBranchesCommand.runCommand',
            [None, None, {}, ['list', 'branches']])


class BranchesPluginTest(rbuildhelp.RbuildHelper):
    def testList(self):
        handle = self.getRbuildHandle()

        mock.mockMethod(handle.facade.rbuilder.getProjectBranches)

        handle.Branches.list('project')
        handle.facade.rbuilder.getProjectBranches._mock.assertCalled('project')
