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
import robj

from rbuild_test import rbuildhelp


class EnableTest(rbuildhelp.RbuildHelper):
    def testEnableArgParse(self):
        self.getRbuildHandle()
        self.checkRbuild(
            'enable label',
            'rbuild_plugins.enable.EnablePlatformCommand.runCommand',
            [None, None, {}, ['rbuild', 'enable', 'label']],
            )
        self.checkRbuild(
            'disable label',
            'rbuild_plugins.enable.EnablePlatformCommand.runCommand',
            [None, None, {}, ['rbuild', 'disable', 'label']],
            )

    def testEnableCmdline(self):
        handle = self.getRbuildHandle(mock.MockObject())
        handle.EnablePlatform.registerCommands()
        handle.EnablePlatform.initialize()
        mock.mockMethod(handle.EnablePlatform.enable)
        mock.mockMethod(handle.EnablePlatform.disable)

        cmd = handle.Commands.getCommandClass('enable')()
        self.assertRaises(
            errors.ParseError,
            cmd.runCommand,
            handle,
            {},
            ['rbuild', 'enable'],
            )

        self.assertRaises(
            errors.ParseError,
            cmd.runCommand,
            handle,
            {},
            ['rbuild', 'disable'],
            )

        cmd.runCommand(handle, {}, ['rbuild', 'disable', 'label'])
        handle.EnablePlatform.disable._mock.assertCalled('label')
        handle.EnablePlatform.enable._mock.assertNotCalled()

        cmd.runCommand(handle, {}, ['rbuild', 'enable', 'label'])
        handle.EnablePlatform.disable._mock.assertNotCalled()
        handle.EnablePlatform.enable._mock.assertCalled('label')

    def testUpdatePlatform(self):
        handle = self.getRbuildHandle(mock.MockObject())
        handle.Launch.registerCommands()
        handle.Launch.initialize()

        mock.mockMethod(handle.facade.rbuilder.getPlatform)
        handle.facade.rbuilder.getPlatform._mock.setReturn(None, 'no label')
        self.assertRaises(
            errors.PluginError,
            handle.EnablePlatform._updatePlatform,
            'no label',
            True,
            )

        _platform = mock.MockObject()
        _platform._mock.set(enabled=None)
        handle.facade.rbuilder.getPlatform._mock.setReturn(_platform, 'label')
        handle.EnablePlatform._updatePlatform('label', True)
        self.assertEqual(_platform.enabled, True)

        _platform._mock.set(enabled=None)
        handle.EnablePlatform._updatePlatform('label', False)
        self.assertEqual(_platform.enabled, False)

    def testUnauthorizedAccess(self):
        '''Regression test for APPENG-2791'''
        handle = self.getRbuildHandle(mock.MockObject())
        handle.Launch.registerCommands()
        handle.Launch.initialize()

        mock.mockMethod(handle.facade.rbuilder.getPlatform)
        handle.facade.rbuilder.getPlatform._mock.setReturn(None, 'no label')
        self.assertRaises(
            errors.PluginError,
            handle.EnablePlatform._updatePlatform,
            'no label',
            True,
            )

        _platform = mock.MockObject()
        _platform._mock.set(enabled=None)
        _platform.persist._mock.raiseErrorOnAccess(
            robj.errors.HTTPUnauthorizedError(
                uri='http://localhost',
                status='401',
                reason='Unauthorized',
                response=None,
                ))
        handle.facade.rbuilder.getPlatform._mock.setReturn(_platform, 'label')
        err = self.assertRaises(
            errors.PluginError,
            handle.EnablePlatform._updatePlatform
            ,'label',
            True,
            )
        self.assertIn('not authorized', str(err))
