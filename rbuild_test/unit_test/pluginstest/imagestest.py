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
        handle.List.registerCommands()
        handle.Delete.initialize()
        handle.Images.initialize()
        cmd = handle.Commands.getCommandClass('delete')()

        mock.mockMethod(handle.Images.delete)

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


class ListImagesTest(rbuildhelp.RbuildHelper):
    def testCommand(self):
        self.getRbuildHandle()
        self.checkRbuild('list images',
            'rbuild_plugins.images.ListImagesCommand.runCommand',
            [None, None, {}, ['list', 'images']])
        self.checkRbuild('list images 1 2',
            'rbuild_plugins.images.ListImagesCommand.runCommand',
            [None, None, {}, ['list', 'images', '1', '2']])

    def testLatestImages(self):
        '''Regression test for APPENG-2788'''
        from rbuild.pluginapi import command
        handle = self.getRbuildHandle(mock.MockObject())
        handle.List.registerCommands()
        handle.Delete.registerCommands()
        handle.Images.initialize()

        mock.mock(handle, 'ui')

        _latest = mock.MockObject()
        _latest._mock.set(id='http://localhost/latest')
        _resource = mock.MockObject()
        _resource._node._mock.set(latest_files=[_latest])
        mock.mock(command.ListCommand, '_list', _resource)

        cmd = handle.Commands.getCommandClass('list')()
        cmd.runCommand(handle, {}, ['rbuild', 'list', 'images'])
        handle.ui.write._mock.assertCalled('http://localhost/latest')

        _latest._mock.set(id='http://localhost/latest%20image')
        cmd.runCommand(handle, {}, ['rbuild', 'list', 'images'])
        handle.ui.write._mock.assertCalled(
            'http://localhost/latest%%20image')


class ImagesPluginTest(rbuildhelp.RbuildHelper):
    def testDelete(self):
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
        handle.product.getBaseLabel._mock.setReturn('branch')
        handle.productStore.getActiveStageName._mock.setReturn('stage')
        mock.mockMethod(handle.facade.rbuilder.getImages, None)

        handle.Images.delete(10)
        handle.facade.rbuilder.getImages._mock.assertCalled(
            image_id=10, project='project', branch='branch', stage='stage')
        handle.ui.write._mock.assertCalled("No image found with id '10'")

    def testDeleteNoProduct(self):
        handle = self.getRbuildHandle()

        mock.mockMethod(handle.facade.rbuilder.getImages)

        err = self.assertRaises(
            errors.PluginError,
            handle.Images.delete,
            10,
            )
        self.assertIn('rbuild init', str(err))
        handle.facade.rbuilder.getImages._mock.assertNotCalled()

    def testDeleteNoStage(self):
        handle = self.getRbuildHandle()

        mock.mock(handle, 'productStore')
        mock.mock(handle, 'product')
        handle.product.getProductShortname._mock.setReturn('project')
        handle.productStore._mock.set(_currentStage=None)

        mock.mockMethod(handle.facade.rbuilder.getImages)

        err = self.assertRaises(
            errors.PluginError,
            handle.Images.delete,
            10,
            )
        self.assertIn('not a valid stage', str(err))
        handle.facade.rbuilder.getImages._mock.assertNotCalled()

    def testList(self):
        handle = self.getRbuildHandle()
        mock.mockMethod(handle.facade.rbuilder.getImages)
        mock.mock(handle, 'product')
        mock.mock(handle, 'productStore')
        handle.product.getProductShortname._mock.setReturn('project')
        handle.productStore.getActiveStageName._mock.setReturn('stage')
        handle.product.getBaseLabel._mock.setReturn('branch')

        handle.Images.list()
        handle.facade.rbuilder.getImages._mock.assertCalled(
            project='project', branch='branch', stage='stage')

    def testListNoProduct(self):
        handle = self.getRbuildHandle()
        mock.mockMethod(handle.facade.rbuilder.getImages)

        err = self.assertRaises(
            errors.PluginError,
            handle.Images.list,
            )
        self.assertIn('rbuild init', str(err))

    def testListNoStage(self):
        handle = self.getRbuildHandle()
        mock.mockMethod(handle.facade.rbuilder.getImages)
        mock.mock(handle, 'product')
        mock.mock(handle, 'productStore')
        handle.product.getProductShortname._mock.setReturn('project')
        handle.productStore.getActiveStageName._mock.raiseErrorOnAccess(
            errors.RbuildError('No current stage'))

        err = self.assertRaises(
            errors.RbuildError,
            handle.Images.list,
            )
        self.assertEqual('No current stage', str(err))
        handle.facade.rbuilder.getImages._mock.assertNotCalled()

    def testShow(self):
        handle = self.getRbuildHandle()

        mock.mock(handle, 'productStore')
        mock.mock(handle, 'product')
        handle.product.getProductShortname._mock.setReturn('project')
        handle.productStore.getActiveStageName._mock.setReturn('stage')
        handle.product.getBaseLabel._mock.setReturn('branch')
        mock.mockMethod(handle.facade.rbuilder.getImages, ['image'])

        rv = handle.Images.show(10)
        self.assertEqual(rv, 'image')
        handle.facade.rbuilder.getImages._mock.assertCalled(
            image_id=10, project='project', branch='branch', stage='stage')

    def testShowMissing(self):
        handle = self.getRbuildHandle()

        mock.mock(handle, 'productStore')
        mock.mock(handle, 'product')
        mock.mock(handle, 'ui')
        handle.product.getProductShortname._mock.setReturn('project')
        handle.product.getBaseLabel._mock.setReturn('branch')
        handle.productStore.getActiveStageName._mock.setReturn('stage')
        mock.mockMethod(handle.facade.rbuilder.getImages, None)

        handle.Images.show(10)
        handle.facade.rbuilder.getImages._mock.assertCalled(
            image_id=10, project='project', branch='branch', stage='stage')

    def testShowNoProduct(self):
        handle = self.getRbuildHandle()

        mock.mockMethod(handle.facade.rbuilder.getImages)

        err = self.assertRaises(
            errors.PluginError,
            handle.Images.delete,
            10,
            )
        self.assertIn('rbuild init', str(err))
        handle.facade.rbuilder.getImages._mock.assertNotCalled()

    def testShowNoStage(self):
        handle = self.getRbuildHandle()

        mock.mock(handle, 'productStore')
        mock.mock(handle, 'product')
        handle.product.getProductShortname._mock.setReturn('project')
        handle.productStore._mock.set(_currentStage=None)

        mock.mockMethod(handle.facade.rbuilder.getImages)

        err = self.assertRaises(
            errors.PluginError,
            handle.Images.show,
            10,
            )
        self.assertIn('not a valid stage', str(err))
        handle.facade.rbuilder.getImages._mock.assertNotCalled()
