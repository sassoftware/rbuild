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
from smartform import descriptor_errors
from testutils import mock

from rbuild_test import rbuildhelp


TARGET_CONFIG = '''\
---
alias: foo.com
name: Foo
description: Foo vCenter
zone: Local rBuilder
defaultDiskProvisioning: thin
username: test
password: tclmeSAS
'''

INCOMPLETE_TARGET_CONFIG = '''\
---
alias: foo.com
name: Foo
description: Foo vCenter
zone: Local rBuilder
'''


class CreateTargetTest(rbuildhelp.RbuildHelper):

    def testCreateTargetArgParse(self):
        self.getRbuildHandle()
        self.checkRbuild(
            'create target --list --from-file=file vmware',
            'rbuild_plugins.createtarget.CreateTargetCommand.runCommand',
            [None, None, {
                'list': True,
                'from-file': 'file',
                }, ['create', 'target', 'vmware']])

    def testCreateTargetCmdlineNoTargetType(self):
        handle = self.getRbuildHandle(mock.MockObject())
        handle.Create.registerCommands()
        handle.CreateTargetPlugin.initialize()
        rbuilder = handle.facade.rbuilder

        mock.mockMethod(rbuilder.getTargetDescriptor, None)

        cmd = handle.Commands.getCommandClass('create')()

        self.assertRaises(
            errors.RbuildError,
            cmd.runCommand,
            handle,
            {'list': False},
            ['rbuild', 'create', 'target', 'vmware'],
            )

    def testCreateTargetCmdline(self):
        from plugins.createtarget import descriptor
        _ddata = mock.mockClass(descriptor.ConfigurationDescriptor)
        _cred_ddata = mock.mockClass(descriptor.ConfigurationDescriptor)
        _target = mock.MockObject()
        _descr = mock.MockObject()
        _descr.createDescriptorData._mock.setDefaultReturns(
            [_ddata, _cred_ddata])

        mock.mock(descriptor, 'ConfigurationDescriptor', _descr)

        handle = self.getRbuildHandle(mock.MockObject())
        handle.Create.registerCommands()
        handle.CreateTargetPlugin.initialize()
        rbuilder = handle.facade.rbuilder

        mock.mockMethod(rbuilder.getTargetDescriptor)
        mock.mockMethod(rbuilder.createTarget, _target)
        mock.mockMethod(rbuilder.configureTarget)
        mock.mockMethod(rbuilder.configureTargetCredentials)

        cmd = handle.Commands.getCommandClass('create')()
        cmd.runCommand(
            handle,
            {'list': False},
            ['rbuild', 'create', 'target', 'vmware'],
            )
        rbuilder.getTargetDescriptor._mock.assertCalled('vmware')
        rbuilder.createTarget._mock.assertCalled(_ddata, 'vmware')
        rbuilder.configureTarget._mock.assertCalled(_target, _ddata)
        rbuilder.configureTargetCredentials._mock.assertCalled(
            _target, _cred_ddata)

    def testCreateTargetBadField(self):
        from plugins.createtarget import descriptor
        _descr = mock.MockObject()

        def _createDescriptorData(*args, **kwargs):
            raise descriptor_errors.ConstraintsValidationError('foo')

        _descr._mock.set(createDescriptorData=_createDescriptorData)

        mock.mock(descriptor, 'ConfigurationDescriptor', _descr)

        handle = self.getRbuildHandle(mock.MockObject())
        handle.Create.registerCommands()
        handle.CreateTargetPlugin.initialize()
        rbuilder = handle.facade.rbuilder

        mock.mockMethod(rbuilder.getTargetDescriptor)

        cmd = handle.Commands.getCommandClass('create')()
        self.assertRaises(
            errors.RbuildError,
            cmd.runCommand,
            handle,
            {'list': False},
            ['rbuild', 'create', 'target', 'vmware'],
            )
