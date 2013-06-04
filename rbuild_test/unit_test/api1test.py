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



from testutils import mock
from rbuild_test import rbuildhelp

# need to get at this both ways
import rbuild
from rbuild import api1

from rbuild import rbuildcfg
from rbuild.productstore import abstract, dirstore
from rbuild.internal import pluginloader
from rbuild.facade import conaryfacade


class Api1Test(rbuildhelp.RbuildHelper):
    def setupMockObjects(self):
        self.rbuildconfig = mock.MockObject()
        self.rbuildconfig().pluginDirs = 'pluginDirs'
        self.checkoutProductStore = mock.MockObject()
        self.abstractProductStore = mock.MockObject()
        self.getplugins = mock.MockObject()
        self.getconaryclient = mock.MockObject()
        self.mock(api1.handle.RbuildHandle, 'configClass', self.rbuildconfig)
        self.mock(dirstore, 'CheckoutProductStore', self.checkoutProductStore)
        self.mock(abstract, 'ProductStore', self.abstractProductStore)
        self.mock(pluginloader, 'getPlugins', self.getplugins)
        self.mock(conaryfacade.ConaryFacade, '_getConaryClient', self.getconaryclient)

    def testDefault(self):
        self.setupMockObjects()
        handle = api1.getHandle()
        self.rbuildconfig._mock.assertCalled(readConfigFiles=True)
        self.checkoutProductStore._mock.assertCalled(baseDirectory=None)
        self.getplugins._mock.assertCalled([], self.rbuildconfig().pluginDirs)
        # ensure that both calling conventions work
        handle2 = rbuild.getHandle()

    def testDirectory(self):
        self.setupMockObjects()
        handle = api1.getHandle(dirName='/path')
        self.rbuildconfig._mock.assertCalled(readConfigFiles=True)
        self.checkoutProductStore._mock.assertCalled(baseDirectory='/path')
        self.getplugins._mock.assertCalled([], self.rbuildconfig().pluginDirs)

    def testLabel(self):
        self.setupMockObjects()
        stream = mock.MockObject()
        self.abstractProductStore().getProduct(
            )._getStreamFromRepository._mock.setDefaultReturn((stream, 'nvf'))
        handle = api1.getHandle(prodDefLabel='foo@bar:baz')
        self.rbuildconfig._mock.assertCalled(readConfigFiles=True)
        self.getplugins._mock.assertCalled([], self.rbuildconfig().pluginDirs)
        self.abstractProductStore._mock.assertCalled()
        self.abstractProductStore().getProduct._mock.assertCalled()
        self.getconaryclient._mock.assertCalled()
        self.abstractProductStore().getProduct(
            )._getStreamFromRepository._mock.assertCalled(
                self.getconaryclient(), 'foo@bar:baz')
        stream.seek._mock.assertCalled(0)
        self.abstractProductStore().getProduct(
            ).parseStream._mock.assertCalled(stream)


