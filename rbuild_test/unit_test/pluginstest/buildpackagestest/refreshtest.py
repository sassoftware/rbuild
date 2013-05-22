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
import os.path


from rbuild_test import rbuildhelp
from testutils import mock

from conary.lib import log

from rbuild import errors

class RefreshTest(rbuildhelp.RbuildHelper):
    def testRefreshPackages(self):
        handle = self.getRbuildHandle()
        from rbuild_plugins.build import refresh
        packagePath = self.workDir + '/foo/foo.recipe'

        # Mock the productStore and its needed methods.
        handle.productStore = mock.MockObject()
        packageRecipes = {'foo' : packagePath}
        handle.productStore.getPackagePath._mock.setReturn(packagePath, 'foo')

        mock.mockMethod(handle.facade.conary.refresh)

        rc = refresh.refreshPackages(handle, ['foo'])
        assert(rc is None)
        handle.facade.conary.refresh._mock.assertCalled(
            targetDir=self.workDir+'/foo/foo.recipe')

    def testRefreshAllPackages(self):
        handle = self.getRbuildHandle()
        from rbuild_plugins.build import refresh
        packagePath = self.workDir + '/foo/foo.recipe'

        # Mock the productStore and its needed methods.
        handle.productStore = mock.MockObject()
        packageRecipes = {'foo' : packagePath}
        handle.productStore.getEditedRecipeDicts._mock.setReturn(
                                                        (packageRecipes, {}))
        mock.mockMethod(handle.facade.conary.refresh)

        rc = refresh.refreshAllPackages(handle)
        assert(rc is None)
        handle.facade.conary.refresh._mock.assertCalled(
            targetDir=self.workDir+'/foo')


