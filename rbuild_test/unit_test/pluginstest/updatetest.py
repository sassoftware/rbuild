#!/usr/bin/python
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



import os

from rbuild_test import rbuildhelp
from testutils import mock

from rbuild import errors
from rbuild.internal import main

class UpdateTest(rbuildhelp.RbuildHelper):
    def _getHandle(self):
        handle = self.getRbuildHandle(productStore=mock.MockObject())
        handle.Update.registerCommands()
        handle.Update.initialize()
        return handle

    def testUpdateCommandParsing(self):
        mainHandler = main.RbuildMain()
        handle = self._getHandle()
        cmd = handle.Commands.getCommandClass('update')()
        cmd.setMainHandler(mainHandler)
        handle.productStore.update._mock.setDefaultReturn(None)
        mock.mockMethod(handle.Update.updateByCurrentDirectory)
        mock.mockMethod(handle.Update.updateAllStages)
        mock.mockMethod(handle.Update.updateCurrentStage)
        mock.mockMethod(handle.Update.updateStages)
        from rbuild_plugins import update
        mock.mock(update.UpdateCommand, 'usage')

        cmd.runCommand(handle, {}, ['rbuild', 'update'])
        handle.Update.updateByCurrentDirectory._mock.assertCalled()

        cmd.runCommand(handle, {}, ['rbuild', 'update', 'product'])
        handle.productStore.update._mock.assertCalled()

        cmd.runCommand(handle, {}, ['rbuild', 'update', 'packages'])
        handle.Update.updateAllStages._mock.assertCalled()

        cmd.runCommand(handle, {}, ['rbuild', 'update', 'all'])
        handle.productStore.update._mock.assertCalled()
        handle.Update.updateAllStages._mock.assertCalled()

        cmd.runCommand(handle, {}, ['rbuild', 'update', 'stage'])
        handle.Update.updateCurrentStage._mock.assertCalled()

        cmd.runCommand(handle, {}, ['rbuild', 'update', 'stage', 'foo'])
        handle.Update.updateStages._mock.assertCalled(['foo'])

        cmd.runCommand(handle, {}, ['rbuild', 'update', 'stage', 'foo', 'bar'])
        handle.Update.updateStages._mock.assertCalled(['foo', 'bar'])

        # unknown arguments
        cmd.runCommand(handle, {}, ['rbuild', 'update', 'unknown'])
        update.UpdateCommand.usage._mock.assertCalled()


    def testUpdateByCurrentDirectory(self):
        realExists = os.path.exists
        def mockCONARYExists(path):
            if path == 'CONARY':
                return True
            if path == '.rbuild':
                return False
            return realExists(path)
        def mockdotrbuildExists(path):
            if path == 'CONARY':
                return False
            if path == '.rbuild':
                return True
            return realExists(path)
        def mockNeitherExists(path):
            if path in set(('CONARY', '.rbuild')):
                return False
            return realExists(path)

        handle = self._getHandle()
        handle.productStore.update._mock.setDefaultReturn(None)
        self.mock(os.path, 'exists',
            lambda *args: mockCONARYExists(*args))
        mock.mockMethod(handle.Update.updateCurrentDirectory)
        mock.mockMethod(handle.Update.updateCurrentStage)
        handle.Update.updateByCurrentDirectory()
        handle.Update.updateCurrentDirectory._mock.assertCalled()
        handle.Update.updateCurrentStage._mock.assertNotCalled()
        handle.productStore.update._mock.assertNotCalled()

        self.mock(os.path, 'exists',
            lambda *args: mockdotrbuildExists(*args))
        handle.Update.updateByCurrentDirectory()
        handle.Update.updateCurrentDirectory._mock.assertNotCalled()
        handle.Update.updateCurrentStage._mock.assertNotCalled()
        handle.productStore.update._mock.assertCalled()

        self.mock(os.path, 'exists',
            lambda *args: mockNeitherExists(*args))
        handle.Update.updateByCurrentDirectory()
        handle.Update.updateCurrentDirectory._mock.assertNotCalled()
        handle.Update.updateCurrentStage._mock.assertCalled()
        handle.productStore.update._mock.assertNotCalled()

    def testUpdateAllStages(self):
        handle = self._getHandle()
        handle.productStore.iterStageNames._mock.setDefaultReturn(['foo', 'bar'])
        mock.mockMethod(handle.Update.updateStages)
        handle.Update.updateAllStages()
        handle.Update.updateStages._mock.assertCalled(['foo', 'bar'])

    def testUpdateCurrentStage(self):
        handle = self._getHandle()
        # we have an active stage
        handle.productStore.getActiveStageName._mock.setDefaultReturn('foo')
        mock.mockMethod(handle.Update.updateStages)
        handle.Update.updateCurrentStage()
        handle.Update.updateStages._mock.assertCalled(['foo'])

        # we do not have an active stage
        handle.productStore.getActiveStageName._mock.setDefaultReturn(None)
        self.assertRaises(errors.PluginError, handle.Update.updateCurrentStage)

    def testUpdateStages(self):
        handle = self._getHandle()
        maps = ({'bar': './bar/bar.recipe', 'baz': './baz/baz.recipe'}, {'group-foo': './group-foo/group-foo.recipe'})
        handle.productStore.getEditedRecipeDicts._mock.setDefaultReturn(maps)
        mock.mockMethod(handle.facade.conary.updateCheckout)
        handle.Update.updateStages(['foo'])
        # inverse order
        handle.facade.conary.updateCheckout._mock.assertCalled('./baz')
        handle.facade.conary.updateCheckout._mock.assertCalled('./bar')
        handle.facade.conary.updateCheckout._mock.assertCalled('./group-foo')

    def testUpdateCurrentDirectory(self):
        handle = self._getHandle()
        mock.mockMethod(handle.facade.conary.updateCheckout)
        handle.Update.updateCurrentDirectory()
        handle.facade.conary.updateCheckout._mock.assertCalled(os.getcwd())


