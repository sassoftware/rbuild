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
from rbuild.productstore import dirstore
from testutils import mock

from rbuild_test import rbuildhelp, mockproddef

class EditTest(rbuildhelp.RbuildHelper):
    def newProductDefinition(self):
        self.cfg.initializeFlavors()
        return mockproddef.getProductDefinition(self.cfg)

    def testCommand(self):
        handle = self.getRbuildHandle()
        handle.Edit.registerCommands()
        handle.Edit.initialize()
        cmd = handle.Commands.getCommandClass('edit')()
        mock.mockMethod(handle.Edit.editProductDefinition)
        cmd.runCommand(handle, {}, ['rbuild', 'edit', 'product'])
        handle.Edit.editProductDefinition._mock.assertCalled('rbuild commit')

        cmd.runCommand(handle, dict(message='blip'),
                ['rbuild', 'edit', 'product'])
        handle.Edit.editProductDefinition._mock.assertCalled('blip')

    def testEditProductDefinition(self):
        proddef = self.newProductDefinition()
        projDir = os.path.join(self.workDir, 'myproject')
        prodDefDir = os.path.join(projDir, '.rbuild/product-definition')
        prodDefPath = os.path.join(prodDefDir, 'product-definition.xml')
        os.makedirs(prodDefDir)
        proddef.serialize(file(prodDefPath, "w"))

        productStore = dirstore.CheckoutProductStore(baseDirectory=projDir)
        handle = self.getRbuildHandle(productStore=productStore)
        mock.mock(handle.facade, 'conary')
        facade = handle.facade.conary

        message = "commit message"

        # Return a consistent temp file
        tmpf = handle.Edit._makeTemporaryFile()
        mock.mockMethod(handle.Edit._makeTemporaryFile, tmpf)

        class MockMethod(object):
            def __init__(self):
                self.retval = None
                self.callList = []
                self.realFunction = None
                self._idx = 0

            def __call__(self, *args, **kwargs):
                self.callList.append((args, kwargs))
                if self.realFunction is None:
                    return self.retval
                if isinstance(self.realFunction, list):
                    func = self.realFunction[self._idx]
                    self._idx += 1
                else:
                    func = self.realFunction
                return func(*args, **kwargs)

            def reset(self):
                self._idx = 0
                del self.callList[:]

        invEditor = MockMethod()
        self.mock(handle.Edit, '_invokeEditor', invEditor)

        # Simulate edit error
        invEditor.retval = 1
        self.assertEquals(handle.Edit.editProductDefinition(message), 1)

        tmpf.seek(0); tmpf.truncate(); invEditor.reset()

        # Simulate no change (mtime of file doesn't change)
        invEditor.retval = 0
        self.assertEquals(handle.Edit.editProductDefinition(message), 0)

        tmpf.seek(0); tmpf.truncate(); invEditor.reset()

        def _changedProdDef(stream):
            # Change the proddef
            prod = self.newProductDefinition()
            prod.setProductName('awesome name, changed')
            stream.seek(0); stream.truncate()
            prod.serialize(stream)
            return 0
        invEditor.realFunction = _changedProdDef
        self.assertEquals(handle.Edit.editProductDefinition(message), 0)
        self.assertEquals(len(invEditor.callList), 1)

        facade.commit._mock.assertCalled(prodDefDir, message=message)

        # Test some of the more possible errors

        tmpf.seek(0); tmpf.truncate(); invEditor.reset()
        def _invalidXml(stream):
            stream.seek(0); stream.truncate()
            stream.write("<invalid xml")
            stream.flush()
            return 0
        invEditor.realFunction = _invalidXml

        uiInput = mock.mockMethod(handle.ui.input)
        uiInput._mock.setReturn('n', 'Do you want to retry? (Y/n) ')
        self.assertEquals(handle.Edit.editProductDefinition(message), 3)

        # Invalid xml first, then correct one
        tmpf.seek(0); tmpf.truncate(); invEditor.reset()
        invEditor.realFunction = [ _invalidXml, _invalidXml, _changedProdDef ]
        uiInput._mock.setReturn('y', 'Do you want to retry? (Y/n) ')
        self.assertEquals(handle.Edit.editProductDefinition(message), 0)
        facade.commit._mock.assertCalled(prodDefDir, message=message)

        def _xmlNoNamespace(stream):
            stream.seek(0); stream.truncate()
            stream.write("<productDefinition/>")
            stream.flush()
            return 0

        tmpf.seek(0); tmpf.truncate(); invEditor.reset()
        invEditor.realFunction = _xmlNoNamespace
        uiInput._mock.setReturn('n', 'Do you want to retry? (Y/n) ')
        self.assertEquals(handle.Edit.editProductDefinition(message), 1)

        def _xmlNamespacedNoVersion(stream):
            stream.seek(0); stream.truncate()
            stream.write("<productDefinition xmlns='http://dummy'/>")
            stream.flush()
            return 0

        tmpf.seek(0); tmpf.truncate(); invEditor.reset()
        invEditor.realFunction = _xmlNamespacedNoVersion
        uiInput._mock.setReturn('n', 'Do you want to retry? (Y/n) ')
        self.assertEquals(handle.Edit.editProductDefinition(message), 2)

        # XXX should test an invalid proddef too
