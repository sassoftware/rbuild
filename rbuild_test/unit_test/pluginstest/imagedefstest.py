#
# Copyright (c) SAS Institute Inc.
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
from plugins import imagedefs
from testutils import mock

from rbuild_test import rbuildhelp


class AbstractImageDefsTest(rbuildhelp.RbuildHelper):
    def setUp(self):
        rbuildhelp.RbuildHelper.setUp(self)
        self.handle = self.getRbuildHandle()
        self.handle.Create.registerCommands()
        self.handle.Delete.registerCommands()
        self.handle.List.registerCommands()
        self.handle.ImageDefs.registerCommands()
        self.handle.Create.initialize()
        self.handle.Delete.initialize()
        self.handle.List.initialize()
        self.handle.ImageDefs.initialize()


class CreateImageDefTest(AbstractImageDefsTest):
    def testArgParse(self):
        self.checkRbuild(
            'create imagedef --message=foo --from-file=fromFile'
            ' --to-file=toFile type arch',
            'rbuild_plugins.imagedefs.CreateImageDefCommand.runCommand',
            [None, None, {
                'message': 'foo',
                'from-file': 'fromFile',
                'to-file': 'toFile',
                }, ['create', 'imagedef', 'type', 'arch']])

    def testCmdLine(self):
        handle = self.handle

        mock.mockMethod(handle.DescriptorConfig.readConfig)
        mock.mockMethod(handle.DescriptorConfig.writeConfig)
        mock.mockMethod(handle.ImageDefs.create)
        mock.mockMethod(handle.facade.rbuilder.getImageTypes)

        _amiImage = mock.MockObject(name="amiImage")
        _vmwareImage = mock.MockObject(name="vmwareImage")
        handle.facade.rbuilder.getImageTypes._mock.setReturn(
            [_amiImage, _vmwareImage])

        cmd = handle.Commands.getCommandClass('create')()

        argSet = {}
        args = ['rbuild', 'create', 'imagedef']
        err = self.assertRaises(
            errors.ParseError, cmd.runCommand, handle, argSet, args)
        self.assertEqual(
            str(err), "'imagedef' missing 2 command parameter(s): TYPE, ARCH")

        args = ['rbuild', 'create', 'imagedef', 'foo']
        err = self.assertRaises(
            errors.ParseError, cmd.runCommand, handle, argSet, args)
        self.assertEqual(
            str(err), "'imagedef' missing 1 command parameter(s): ARCH")

        args = ['rbuild', 'create', 'imagedef', 'foo', 'bar']
        err = self.assertRaises(
            errors.PluginError, cmd.runCommand, handle, argSet, args)
        self.assertEqual(str(err), "No such image type 'foo'."
            " Run `rbuild list imagetypes` to see valid image types")

        args = ['rbuild', 'create', 'imagedef', 'amiImage', 'bar']
        err = self.assertRaises(
            errors.PluginError, cmd.runCommand, handle, argSet, args)
        self.assertEqual(
            str(err), "No such architecture 'bar'. Valid architectures are:"
            " x86 and x86_64")

        args = ['rbuild', 'create', 'imagedef', 'amiImage', 'x86']
        cmd.runCommand(handle, argSet, args)
        handle.DescriptorConfig.readConfig._mock.assertNotCalled()
        handle.ImageDefs.create._mock.assertCalled(
            _amiImage, 'x86', None)
        handle.DescriptorConfig.writeConfig._mock.assertNotCalled()

        argSet = {'from-file': 'inFile'}
        cmd.runCommand(handle, argSet, args)
        handle.DescriptorConfig.readConfig._mock.assertCalled('inFile')
        handle.ImageDefs.create._mock.assertCalled(
            _amiImage, 'x86', None)
        handle.DescriptorConfig.writeConfig._mock.assertNotCalled()

        argSet = {'from-file': 'inFile', 'to-file': 'outFile'}
        cmd.runCommand(handle, argSet, args)
        handle.DescriptorConfig.readConfig._mock.assertCalled('inFile')
        handle.ImageDefs.create._mock.assertCalled(
            _amiImage, 'x86', None)
        handle.DescriptorConfig.writeConfig._mock.assertCalled('outFile')

        argSet = {'from-file': 'inFile', 'to-file': 'outFile',
                  'message': 'a message'}
        cmd.runCommand(handle, argSet, args)
        handle.DescriptorConfig.readConfig._mock.assertCalled('inFile')
        handle.ImageDefs.create._mock.assertCalled(
            _amiImage, 'x86', 'a message')
        handle.DescriptorConfig.writeConfig._mock.assertCalled('outFile')


class ListImageDefsTest(AbstractImageDefsTest):
    def testCommand(self):
        self.checkRbuild('list imagedefs',
            'rbuild_plugins.imagedefs.ListImageDefsCommand.runCommand',
            [None, None, {}, ['list', 'imagedefs']])


class ImageDefsPluginTest(AbstractImageDefsTest):
    def testList(self):
        handle = self.handle
        mock.mockMethod(handle.facade.rbuilder.getImageDefs)
        mock.mock(handle, 'product')
        mock.mock(handle, 'productStore')
        handle.product.getProductShortname._mock.setReturn('project')
        handle.product.getProductVersion._mock.setReturn('branch')

        handle.ImageDefs.list()
        handle.facade.rbuilder.getImageDefs._mock.assertCalled(
            product='project', version='branch')

    def testListNoProduct(self):
        handle = self.handle
        mock.mockMethod(handle.facade.rbuilder.getImages)

        err = self.assertRaises(errors.MissingProductStoreError,
            handle.ImageDefs.list)
        self.assertIn('rbuild init', str(err))

    def testDelete(self):
        handle = self.handle
        mock.mockMethod(handle.facade.rbuilder.getImageDefs)
        mock.mock(handle, 'product')
        mock.mock(handle, 'productStore')
        mock.mock(handle.ui, 'getYn')
        handle.product.getProductShortname._mock.setReturn('project')
        handle.product.getProductVersion._mock.setReturn('branch')

        class MockBuildDefinition(object):
            """ substitutes for both the robj and the product build definitions """
            def __init__(self, name):
                self.name = name
            def export(self, f, level=0, namespace_=''):
                """ this will create 'IDs' that are md5sums of the name """
                f.write(self.name)
        buildDefinitions = [ MockBuildDefinition('one'), MockBuildDefinition('two'), ]
        handle.product._mock.set(buildDefinition=buildDefinitions)
        handle.facade.rbuilder.getImageDefs._mock.setReturn(
                [ buildDefinitions[0] ],
                id='f97c5d29941bfb1b2fdab0874906ab82', product='project', version='branch')
        handle.ui.getYn._mock.setReturn(True, "Delete one?", default=False)
        handle.productStore.getProductDefinitionXmlPath._mock.setReturn(
                '%s/productstore.xml' % self.workDir)

        handle.ImageDefs.delete('f97c5d29941bfb1b2fdab0874906ab82')

        self.assertEquals(len(buildDefinitions), 1)
        self.assertEquals(buildDefinitions[0].name, 'two')
        handle.productStore.commit._mock.assertCalled(message="Remove image def one")
        handle.productStore.update._mock.assertCalled()

    def testDeleteNoImageDefs(self):
        handle = self.handle
        mock.mockMethod(handle.facade.rbuilder.getImageDefs)
        mock.mock(handle, 'product')
        mock.mock(handle, 'productStore')
        mock.mock(handle.ui, 'getYn')
        handle.product.getProductShortname._mock.setReturn('project')
        handle.product.getProductVersion._mock.setReturn('branch')

        buildDefinitions = [ ]
        handle.product._mock.set(buildDefinition=buildDefinitions)
        handle.facade.rbuilder.getImageDefs._mock.setReturn(
                [ ],
                id='f97c5d29941bfb1b2fdab0874906ab82', product='project', version='branch')

        err = self.assertRaises(Exception,
                handle.ImageDefs.delete, 'f97c5d29941bfb1b2fdab0874906ab82')
        self.assertEquals(len(buildDefinitions), 0)
        handle.productStore.update._mock.assertNotCalled()
        handle.ui.getYn._mock.assertNotCalled()
        self.assertEquals(str(err), "Unable to find imagedef with id "
                "'f97c5d29941bfb1b2fdab0874906ab82' on branch version of "
                "project project")
