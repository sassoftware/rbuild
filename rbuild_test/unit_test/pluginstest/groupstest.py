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


class AbstractGroupsTest(rbuildhelp.RbuildHelper):
    def setUp(self):
        rbuildhelp.RbuildHelper.setUp(self)
        self.handle = self.getRbuildHandle()
        self.handle.List.registerCommands()
        self.handle.Groups.registerCommands()
        self.handle.List.initialize()
        self.handle.Groups.initialize()


class ListGroupsTest(AbstractGroupsTest):
    def testCommand(self):
        self.checkRbuild('list groups',
            'rbuild_plugins.groups.ListGroupsCommand.runCommand',
            [None, None, {}, ['list', 'groups']])


class GroupsTest(AbstractGroupsTest):
    def testList(self):
        handle = self.handle

        mock.mock(handle, 'product')
        mock.mock(handle, 'productStore')

        _group_1 = mock.MockObject()
        _group_1._mock.set(timeStamp=1)
        _group_2 = mock.MockObject()
        _group_2._mock.set(timeStamp=2)
        _group_3 = mock.MockObject()
        _group_3._mock.set(timeStamp=3)
        mock.mockMethod(handle.facade.rbuilder.getGroups,
            [_group_1, _group_3,  _group_2])

        self.assertEqual([_group_3, _group_2, _group_1], handle.Groups.list())
