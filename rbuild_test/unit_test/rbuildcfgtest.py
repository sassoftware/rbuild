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


"""
Test various methods of the RbuildConfiguration object.
"""

from rbuild_test import rbuildhelp

import tempfile

from rbuild import rbuildcfg

class ConfigTest(rbuildhelp.RbuildHelper):
    def testWriteCheckoutFile(self):
        """
        Validate the output of the function used to write the rbuildrc
        in new product checkouts.
        """
        config = rbuildcfg.RbuildConfiguration()
        config.configLine('name Mr. User')
        config.configLine('contact mr.user@foo.com')
        config.configLine('repositoryMap []')
        config.configLine('repositoryMap foo.com https://repo.foo.com/conary/')
        config.configLine('repositoryMap bar.com https://dev.bar.com/conary/')
        config.configLine('user someuser somepassword')
        config.configLine('serverUrl http://myrbuilder.foo')
        config.configLine('signatureKey ASDF')
        config.configLine('signatureKeyMap foo FDSA')
        config.configLine('quiet True')

        dumpFile = tempfile.NamedTemporaryFile()
        config.writeCheckoutFile(dumpFile.name)
        dumpFile.seek(0)
        dump = dumpFile.read()

        expected = '''# contact (Default: None) (At `rbuild init': mr.user@foo.com)
# name (Default: None) (At `rbuild init': Mr. User)
# pluginDirs (Default: /usr/share/rbuild/plugins:~/.rbuild/plugins.d) (At `rbuild init': /usr/share/rbuild/plugins:~/.rbuild/plugins.d)
# quiet (Default: False) (At `rbuild init': True)
# repositoryMap (Default: [])
repositoryMap             foo.com                   https://repo.foo.com/conary/
repositoryMap             bar.com                   https://dev.bar.com/conary/
# rmakePluginDirs (Default: /usr/share/rmake/plugins:~/.rmake/plugins.d) (At `rbuild init': /usr/share/rmake/plugins:~/.rmake/plugins.d)
# rmakeUrl (Default: None) (At `rbuild init': None)
# serverUrl (Default: None) (At `rbuild init': http://myrbuilder.foo)
# signatureKey (Default: None) (At `rbuild init': ASDF)
# signatureKeyMap (Default: []) (At `rbuild init': foo FDSA)
'''

        self.failUnlessEqual(dump, expected)

