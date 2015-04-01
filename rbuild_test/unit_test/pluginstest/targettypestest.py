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


class AbstractTargetTypesTest(rbuildhelp.RbuildHelper):
    def setUp(self):
        rbuildhelp.RbuildHelper.setUp(self)
        self.handle = self.getRbuildHandle()
        self.handle.List.registerCommands()
        self.handle.TargetTypes.registerCommands()
        self.handle.List.initialize()
        self.handle.TargetTypes.initialize()


class ListTargetTypesTest(AbstractTargetTypesTest):
    def testCommand(self):
        self.checkRbuild('list targettypes',
            'rbuild_plugins.targettypes.ListTargetTypesCommand.runCommand',
            [None, None, {}, ['list', 'targettypes']])


class TargetTypesTest(AbstractTargetTypesTest):
    def testList(self):
        handle = self.handle

        _targetType1 = mock.MockObject(name="targettype1")
        _targetType2 = mock.MockObject(name="targettype2")
        mock.mockMethod(handle.facade.rbuilder.getTargetTypes,
            [_targetType1, _targetType2])

        self.assertEqual([_targetType1, _targetType2],
                         handle.TargetTypes.list())
