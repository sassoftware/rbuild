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


class AbstractImageTypesTest(rbuildhelp.RbuildHelper):
    def setUp(self):
        rbuildhelp.RbuildHelper.setUp(self)
        self.handle = self.getRbuildHandle()
        self.handle.List.registerCommands()
        self.handle.ImageTypes.registerCommands()
        self.handle.List.initialize()
        self.handle.ImageTypes.initialize()


class ListImageTypesTest(AbstractImageTypesTest):
    def testCommand(self):
        self.checkRbuild('list imagetypes',
            'rbuild_plugins.imagetypes.ListImageTypesCommand.runCommand',
            [None, None, {}, ['list', 'imagetypes']])


class ImageTypesTest(AbstractImageTypesTest):
    def testList(self):
        handle = self.handle

        mock.mockMethod(handle.facade.rbuilder.getImageTypes,
            ["image1", "image2"])

        self.assertEqual(["image1", "image2"], handle.ImageTypes.list())

