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


class AbstractUsersTest(rbuildhelp.RbuildHelper):
    def setUp(self):
        rbuildhelp.RbuildHelper.setUp(self)
        handle = self.getRbuildHandle()
        handle.Create.registerCommands()
        handle.Delete.registerCommands()
        handle.Edit.registerCommands()
        handle.List.registerCommands()
        handle.Users.registerCommands()
        handle.Create.initialize()
        handle.Delete.initialize()
        handle.Edit.initialize()
        handle.List.initialize()
        handle.Users.initialize()
        self.handle = handle


class ListUsersTest(AbstractUsersTest):
    def testCommand(self):
        self.getRbuildHandle()
        self.checkRbuild('list users',
            'rbuild_plugins.users.ListUsersCommand.runCommand',
            [None, None, {}, ['list', 'users']])
        self.checkRbuild('list users 1 2',
            'rbuild_plugins.users.ListUsersCommand.runCommand',
            [None, None, {}, ['list', 'users', '1', '2']])
