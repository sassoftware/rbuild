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


import testsuite

from rbuild_test import rbuildhelp
from testrunner import pathManager

import os
from testutils import mock

from conary.lib import util

class InitTest(rbuildhelp.CommandTest):
    def testInit(self):
        self.getRbuildHandle()
        from rbuild_plugins import config
        mock.mock(config.Config, 'isComplete', lambda: True)
        self.addProductDefinition(shortName='foo',
                                  upstream=['group-dist=localhost@rpl:linux'])
        txt = self.runCommand('init localhost@rpl:foo-1')
        self.assertEquals(txt, 'Created checkout for localhost@foo:foo-1 at foo-1\n')
        self.verifyFile('foo-1/stable/.stage', 'stable\n')
        self.verifyFile('foo-1/qa/.stage', 'qa\n')
        self.verifyFile('foo-1/devel/.stage', 'devel\n')
        assert(os.path.exists('foo-1/.rbuild/rbuildrc'))
        self.assertEquals(os.stat('foo-1/.rbuild/rbuildrc').st_mode & 0777, 0600)
        # confirm that the cached product directory looks the same as the
        # fresh one
        self.initProductDirectory('foo2')
        try:
            for root, dirs, files in os.walk('foo2'):
                for f in files:
                    if f == 'CONARY':
                        continue
                    if f == 'product-definition.xml':
                        # unfortunately, this file looks different
                        # under addProductDefinition now because it
                        # has arch-specific flavors for building.
                        continue
                    self.verifyFile('foo-1%s/%s' % (root[4:], f),
                                    open('%s/%s' % (root, f)).read())
                for d in dirs:
                    assert os.path.exists('foo-1%s/%s' % (root[4:], d))
        except Exception, err:
            os.chdir('foo-1')
            util.execute(
                'tar -czf foo-product.tgz * .rbuild/* '
                '--exclude ".rbuild/rbuildrc"')
            errorStr = str(err) + """
New tarball at %s/foo-product.tgz.  
Run:
   cp %s/foo-product.tgz %s
To update the archived product definition
""" % (os.getcwd(), os.getcwd(), pathManager.getPath("RBUILD_ARCHIVE_PATH"))
            raise RuntimeError(errorStr)

    def testInitByParts(self):
        pass

