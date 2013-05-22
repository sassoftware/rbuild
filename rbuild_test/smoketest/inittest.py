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

class InitTest(rbuildhelp.RbuildHelper):

    def testInit(self):
        # Test whether we can create a product checkout, and whether that
        # product checkout has the right files in it.
        self.rbuildCfg.serverUrl = None
        self.addProductDefinition(shortName='foo')
        handle = self.getRbuildHandle()
        productVersion = handle.Init.getProductVersionByLabel(
                                                    'localhost@rpl:foo-1')
        handle.Init.createProductDirectory(productVersion,
                                           self.workDir + '/foo')
        assert(os.path.exists(self.workDir + '/foo/.rbuild/rbuildrc'))
        assert(os.path.exists(self.workDir + '/foo/stable/.stage'))
        assert(os.path.exists(self.workDir + '/foo/stable/conaryrc'))
        assert(os.path.exists(self.workDir + '/foo/qa/.stage'))
        assert(os.path.exists(self.workDir + '/foo/qa/conaryrc'))
        assert(os.path.exists(self.workDir + '/foo/devel/.stage'))
        assert(os.path.exists(self.workDir + '/foo/devel/conaryrc'))


