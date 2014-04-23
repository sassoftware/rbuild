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


class AbstractTargetTest(rbuildhelp.RbuildHelper):
    def setUp(self):
        rbuildhelp.RbuildHelper.setUp(self)
        self.handle = self.getRbuildHandle(mock.MockObject())
        self.handle.Create.registerCommands()
        self.handle.Delete.registerCommands()
        self.handle.List.registerCommands()
        self.handle.Targets.registerCommands()
        self.handle.Create.initialize()
        self.handle.Delete.initialize()
        self.handle.List.initialize()
        self.handle.Targets.initialize()


class CreateTargetTest(AbstractTargetTest):
    def testCreateTargetArgParse(self):
        self.checkRbuild(
            'create target --list --from-file=file --to-file=toFile vmware',
            'rbuild_plugins.targets.CreateTargetCommand.runCommand',
            [None, None, {
                'list': True,
                'from-file': 'file',
                'to-file': 'toFile',
                }, ['create', 'target', 'vmware']])

    def testCreateTargetCmdline(self):
        handle = self.handle

        mock.mockMethod(handle.DescriptorConfig.readConfig)
        mock.mockMethod(handle.DescriptorConfig.writeConfig)
        mock.mockMethod(handle.Targets.createTarget)
        mock.mockMethod(handle.Targets.configureTargetCredentials)
        handle.Targets.createTarget._mock.setReturn('target', 'vmware')

        cmd = handle.Commands.getCommandClass('create')()

        err = self.assertRaises(
            errors.ParseError,
            cmd.runCommand,
            handle,
            {'list': False},
            ['rbuild', 'create', 'target'],
            )
        self.assertEqual(
            str(err), "'target' missing 1 command parameter(s): TYPE")

        cmd.runCommand(
            handle,
            {'list': False},
            ['rbuild', 'create', 'target', 'vmware'],
            )
        handle.DescriptorConfig.readConfig._mock.assertNotCalled()
        handle.Targets.createTarget._mock.assertCalled('vmware')
        handle.Targets.configureTargetCredentials\
            ._mock.assertCalled('target')

        cmd.runCommand(
            handle,
            {'list': False, 'from-file': 'foo'},
            ['rbuild', 'create', 'target', 'vmware'],
            )
        handle.DescriptorConfig.readConfig._mock.assertCalled('foo')
        handle.Targets.createTarget._mock.assertCalled('vmware')
        handle.Targets.configureTargetCredentials\
            ._mock.assertCalled('target')
        handle.DescriptorConfig.writeConfig._mock.assertNotCalled()

        cmd.runCommand(
            handle,
            {'list': False, 'to-file': 'foo'},
            ['rbuild', 'create', 'target', 'vmware'],
            )
        handle.DescriptorConfig.readConfig._mock.assertNotCalled()
        handle.Targets.createTarget._mock.assertCalled('vmware')
        handle.Targets.configureTargetCredentials\
            ._mock.assertCalled('target')
        handle.DescriptorConfig.writeConfig._mock.assertCalled('foo')


class ListTargetsTest(AbstractTargetTest):
    def testCommandParsing(self):
        handle = self.handle
        cmd = handle.Commands.getCommandClass('list')()

        mock.mockMethod(handle.Targets.list)

        cmd.runCommand(handle, {}, ['rbuild', 'list', 'targets'])
        handle.Targets.list._mock.assertCalled()

    def testCommand(self):
        self.checkRbuild('list targets',
            'rbuild_plugins.targets.ListTargetsCommand.runCommand',
            [None, None, {}, ['list', 'targets']])


class TargetsPluginTest(AbstractTargetTest):
    def testList(self):
        handle = self.handle

        mock.mockMethod(handle.facade.rbuilder.getTargets)

        handle.Targets.list()
        handle.facade.rbuilder.getTargets._mock.assertCalled()
