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



from rbuild_test import rbuildhelp
from testutils import mock

from rbuild import errors
from rbuild import handle
from rbuild import rbuildcfg
from rbuild import ui

class HandleTest(rbuildhelp.RbuildHelper):

    def preHook(self, *args, **kw):
        print 'hello world'

    def postHook(self, rv, *args, **kw):
        return rv

    def testInstallApiHook(self):
        h = self.getRbuildHandle()

        err = self.assertRaises(errors.MissingPluginError,
                                h.installPrehook, self.testInstallApiHook,
                                self.preHook)
        self.assertEquals(err.pluginName, 'HandleTest')

        err = self.assertRaises(errors.MissingPluginError,
                                h.installPosthook, self.testInstallApiHook,
                                self.postHook)
        self.assertEquals(err.pluginName, 'HandleTest')

        #pylint: disable-msg=E1111
        mockedPre = mock.mockMethod(h.Config._installPrehook)
        h.installPrehook(h.Config.displayConfig, self.preHook)
        mockedPre._mock.assertCalled('displayConfig', self.preHook)
        mockedPost = mock.mockMethod(h.Config._installPosthook)
        h.installPosthook(h.Config.displayConfig, self.postHook)
        mockedPost._mock.assertCalled('displayConfig', self.postHook)

    def testGetConfig(self):
        h = self.getRbuildHandle()
        assert(h.getConfig() is self.rbuildCfg)


    def testGetDefaultConfig(self):
        mock.mock(handle.RbuildHandle, 'configClass')
        h = handle.RbuildHandle(cfg=None, pluginManager=mock.MockObject())
        handle.RbuildHandle.configClass._mock.assertCalled(readConfigFiles=True)

    def testRbuildConfigPath(self):
        productStore = mock.MockObject()
        cfg = mock.MockObject()
        handle = self.getRbuildHandle(cfg=cfg,
                                      pluginManager=mock.MockObject(),
                                      productStore=productStore)
        cfg.read._mock.assertCalled(self.workDir + '/rbuildrc', exception=False)

    def testNoRbuildConfigPath(self):
        class mockProductStore(object):
            def __init__(self):
                self.getRbuildConfigData=mock.MockObject()
            def setHandle(self, handle):
                pass
            def getProduct(self):
                return 'product'
        productStore = mockProductStore()
        cfg = mock.MockObject()
        productStore.getRbuildConfigData._mock.setDefaultReturn('rbuildConfigData')
        handle = self.getRbuildHandle(cfg=cfg,
                                      pluginManager=mock.MockObject(),
                                      productStore=productStore)
        self.assertEquals(handle.product, 'product')
        cfg.readObject._mock.assertCalled('INTERNAL', 'rbuildConfigData')

    def testProxyMissingPlugin(self):
        """
        Handle should raise a KeyError when a missing plugin is accessed
        """

        h = self.getRbuildHandle()
        try:
            h.SomePlugin.dostuff()
        except errors.MissingPluginError, e_value:
            self.failUnlessEqual(e_value.pluginName, "SomePlugin")
            self.failUnlessEqual(str(e_value),
                "Plugin 'SomePlugin' is not loaded")
        else:
            self.fail("Handle did not raise KeyError for missing plugin")

    def testRepr(self):
        """
        Check repr() values with and without a product loaded
        """

        handle1 = self.getRbuildHandle()
        self.failUnlessEqual(repr(handle1),
            '<RbuildHandle at %s>' % hex(id(handle1)))

        handle2 = self.getRbuildHandle()
        handle2.product = mock.MockObject()
        handle2.product._mock.set(getProductDefinitionLabel=lambda: 'dummy@label')
        self.failUnlessEqual(repr(handle2),
            '<RbuildHandle at %s, product dummy@label>' % hex(id(handle2)))


class Command(object):
    commands = ['foo', 'bar']
class Command2(object):
    commands = ['bam', 'baz']

class CommandManagerTest(rbuildhelp.RbuildHelper):

    def testCommandManager(self):
        cm = handle.CommandManager()
        cm.registerCommand(Command)
        cm.registerCommand(Command2)
        self.assertEquals(cm.getCommandClass('foo'), Command)
        self.assertEquals(cm.getCommandClass('bar'), Command)
        self.assertEquals(cm.getCommandClass('bam'), Command2)
        self.assertEquals(cm.getCommandClass('baz'), Command2)
        self.assertEquals(cm.getAllCommandClasses(), set([Command, Command2]))

