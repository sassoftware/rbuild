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


class DeleteImagesTest(rbuildhelp.RbuildHelper):
    def testCommandParsing(self):
        handle = self.getRbuildHandle()
        handle.Delete.registerCommands()
        handle.Delete.initialize()
        handle.Images.initialize()
        cmd = handle.Commands.getCommandClass('delete')()

        mock.mockMethod(handle.Images.delete)

        err = self.assertRaises(
            errors.PluginError, cmd.runCommand, handle, {},
            ['rbuild', 'delete', 'images'])
        self.assertIn('rbuild init', str(err))

        mock.mock(handle, 'productStore')
        handle.productStore._mock.set(_currentStage=None)

        err = self.assertRaises(
            errors.ParseError, cmd.runCommand, handle, {},
            ['rbuild', 'delete', 'images'])
        self.assertIn('IMAGEID', str(err))

        cmd.runCommand(handle, {}, ['rbuild', 'delete', 'images', '10', '11'])
        handle.Images.delete._mock.assertCalled('10')
        handle.Images.delete._mock.assertCalled('11')

    def testCommand(self):
        self.getRbuildHandle()
        self.checkRbuild('delete images',
            'rbuild_plugins.images.DeleteImagesCommand.runCommand',
            [None, None, {}, ['delete', 'images']])
        self.checkRbuild('delete images 1 2',
            'rbuild_plugins.images.DeleteImagesCommand.runCommand',
            [None, None, {}, ['delete', 'images', '1', '2']])


class ImagesPluginTest(rbuildhelp.RbuildHelper):
    def testDeleteNoStage(self):
        handle = self.getRbuildHandle()

        mock.mock(handle, 'productStore')
        mock.mock(handle, 'product')
        handle.product.getProductShortname._mock.setReturn('project')
        handle.productStore.getActiveStageName._mock.raiseErrorOnAccess(
            errors.RbuildError('foo'))

        mock.mockMethod(handle.facade.rbuilder.getImages)

        handle.Images.delete(10)
        handle.facade.rbuilder.getImages._mock.assertCalled(
            image_id=10, project='project')

    def testDeleteStage(self):
        handle = self.getRbuildHandle()

        mock.mock(handle, 'productStore')
        mock.mock(handle, 'product')
        handle.product.getProductShortname._mock.setReturn('project')
        handle.productStore.getActiveStageName._mock.setReturn('stage')
        handle.product.getBaseLabel._mock.setReturn('branch')

        mock.mockMethod(handle.facade.rbuilder.getImages)

        handle.Images.delete(10)
        handle.facade.rbuilder.getImages._mock.assertCalled(
            image_id=10, project='project', branch='branch', stage='stage')

    def testDeleteMissing(self):
        handle = self.getRbuildHandle()

        mock.mock(handle, 'productStore')
        mock.mock(handle, 'product')
        mock.mock(handle, 'ui')
        handle.product.getProductShortname._mock.setReturn('project')
        handle.productStore.getActiveStageName._mock.raiseErrorOnAccess(
            errors.RbuildError('foo'))

        mock.mockMethod(handle.facade.rbuilder.getImages, None)

        handle.Images.delete(10)
        handle.facade.rbuilder.getImages._mock.assertCalled(
            image_id=10, project='project')
        handle.ui.write._mock.assertCalled("No image found with id '10'")
