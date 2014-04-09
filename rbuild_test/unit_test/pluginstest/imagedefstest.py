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


class ListImageDefsTest(rbuildhelp.RbuildHelper):
    def testCommand(self):
        self.getRbuildHandle()
        self.checkRbuild('list imagedefs',
            'rbuild_plugins.imagedefs.ListImageDefsCommand.runCommand',
            [None, None, {}, ['list', 'imagedefs']])


class ImageDefsPluginTest(rbuildhelp.RbuildHelper):
    def testList(self):
        handle = self.getRbuildHandle()
        mock.mockMethod(handle.facade.rbuilder.getImageDefs)
        mock.mock(handle, 'product')
        mock.mock(handle, 'productStore')
        handle.product.getProductShortname._mock.setReturn('project')
        handle.product.getProductVersion._mock.setReturn('branch')

        handle.ImageDefs.list()
        handle.facade.rbuilder.getImageDefs._mock.assertCalled(
            product='project', version='branch')

    def testListNoProduct(self):
        handle = self.getRbuildHandle()
        mock.mockMethod(handle.facade.rbuilder.getImages)

        err = self.assertRaises(
            errors.PluginError,
            handle.ImageDefs.list,
            )
        self.assertIn('rbuild init', str(err))
