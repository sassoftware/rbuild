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


class ListTargetsTest(rbuildhelp.RbuildHelper):
    def testCommandParsing(self):
        handle = self.getRbuildHandle()
        handle.List.registerCommands()
        handle.Targets.initialize()
        handle.List.initialize()
        cmd = handle.Commands.getCommandClass('list')()

        mock.mockMethod(handle.Targets.list)

        cmd.runCommand(handle, {}, ['rbuild', 'list', 'targets'])
        handle.Targets.list._mock.assertCalled()

    def testCommand(self):
        self.getRbuildHandle()
        self.checkRbuild('list targets',
            'rbuild_plugins.targets.ListTargetsCommand.runCommand',
            [None, None, {}, ['list', 'targets']])


class TargetsPluginTest(rbuildhelp.RbuildHelper):
    def testList(self):
        handle = self.getRbuildHandle()

        mock.mockMethod(handle.facade.rbuilder.getTargets)

        handle.Targets.list()
        handle.facade.rbuilder.getTargets._mock.assertCalled()
