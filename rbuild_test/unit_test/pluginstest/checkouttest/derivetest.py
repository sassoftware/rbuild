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

class DeriveTest(rbuildhelp.RbuildHelper):
    def _getHandle(self):
        productStore = mock.MockObject(stableReturnValues=True)
        productStore.getRbuildConfigPath._mock.setReturn(
                                                self.workDir + '/rbuildrc')
        handle = self.getRbuildHandle(productStore=productStore)
        handle.Checkout.registerCommands()
        handle.Checkout.initialize()
        from rbuild_plugins.checkout import derive
        return handle, derive

derivedRecipeHeader = """\

class ClassName(DerivedPackageRecipe):
    name = 'foo'
    version = '1.0'

    def setup(r):
        '''
"""

