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


class CreateImageDefTest(rbuildhelp.RbuildHelper):
    def testArgParse(self):
        self.getRbuildHandle()
        self.checkRbuild(
            'create imagedef --message=foo --list --from-file=fromFile'
            ' --to-file=toFile type arch',
            'rbuild_plugins.createimagedef.CreateImageDefCommand.runCommand',
            [None, None, {
                'message': 'foo',
                'list': True,
                'from-file': 'fromFile',
                'to-file': 'toFile',
                }, ['create', 'imagedef', 'type', 'arch']])

    def testCmdLine(self):
        from rbuild_plugins.createimagedef import IMAGEDEF_SPECS
        handle = self.getRbuildHandle(mock.MockObject())
        handle.Create.registerCommands()
        handle.CreateImageDef.initialize()

        mock.mockMethod(handle.DescriptorConfig.readConfig)
        mock.mockMethod(handle.DescriptorConfig.writeConfig)
        mock.mockMethod(handle.CreateImageDef.create)

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
        self.assertEqual(
            str(err), "No such image type 'foo'. Valid image types are: " +
            ', '.join(sorted(IMAGEDEF_SPECS)))

        args = ['rbuild', 'create', 'imagedef', 'ec2', 'bar']
        err = self.assertRaises(
            errors.PluginError, cmd.runCommand, handle, argSet, args)
        self.assertEqual(
            str(err), "No such architecture 'bar'. Valid architectures are:"
            " x86 and x86_64")

        args = ['rbuild', 'create', 'imagedef', 'ec2', 'x86']
        cmd.runCommand(handle, argSet, args)
        handle.DescriptorConfig.readConfig._mock.assertNotCalled()
        handle.CreateImageDef.create._mock.assertCalled(
            'amiImage', 'x86', None)
        handle.DescriptorConfig.writeConfig._mock.assertNotCalled()

        argSet = {'from-file': 'inFile'}
        cmd.runCommand(handle, argSet, args)
        handle.DescriptorConfig.readConfig._mock.assertCalled('inFile')
        handle.CreateImageDef.create._mock.assertCalled(
            'amiImage', 'x86', None)
        handle.DescriptorConfig.writeConfig._mock.assertNotCalled()

        argSet = {'from-file': 'inFile', 'to-file': 'outFile'}
        cmd.runCommand(handle, argSet, args)
        handle.DescriptorConfig.readConfig._mock.assertCalled('inFile')
        handle.CreateImageDef.create._mock.assertCalled(
            'amiImage', 'x86', None)
        handle.DescriptorConfig.writeConfig._mock.assertCalled('outFile')

        argSet = {'from-file': 'inFile', 'to-file': 'outFile',
                  'message': 'a message'}
        cmd.runCommand(handle, argSet, args)
        handle.DescriptorConfig.readConfig._mock.assertCalled('inFile')
        handle.CreateImageDef.create._mock.assertCalled(
            'amiImage', 'x86', 'a message')
        handle.DescriptorConfig.writeConfig._mock.assertCalled('outFile')
