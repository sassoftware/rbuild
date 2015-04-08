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

import os

from conary.lib import cfg

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
        config.configLine('repositoryMap bar.com https://dev.bar.com/conary/')
        config.configLine('repositoryMap foo.com https://repo.foo.com/conary/')
        config.configLine('repositoryUser bar.com baruser barpassword')
        config.configLine('repositoryUser foo.com foouser foopassword')
        config.configLine('user someuser somepassword')
        config.configLine('serverUrl http://myrbuilder.foo')
        config.configLine('signatureKey ASDF')
        config.configLine('signatureKeyMap foo FDSA')
        config.configLine('quiet True')

        dumpFile = tempfile.NamedTemporaryFile()
        config.writeCheckoutFile(dumpFile.name)
        dumpFile.seek(0)
        dump = dumpFile.read()

        expected = '''\
# applianceTemplate (Default: groupSetAppliance) (At `rbuild init': groupSetAppliance)
# contact (Default: None) (At `rbuild init': mr.user@foo.com)
# factoryTemplate (Default: factory) (At `rbuild init': factory)
# groupTemplate (Default: groupSet) (At `rbuild init': groupSet)
# name (Default: None) (At `rbuild init': Mr. User)
# pluginDirs (Default: /usr/share/rbuild/plugins:~/.rbuild/plugins.d) (At `rbuild init': /usr/share/rbuild/plugins:~/.rbuild/plugins.d)
# quiet (Default: False) (At `rbuild init': True)
# recipeTemplate (Default: default) (At `rbuild init': default)
# recipeTemplateDirs (Default: ~/.conary/recipeTemplates:/etc/conary/recipeTemplates) (At `rbuild init': ~/.conary/recipeTemplates:/etc/conary/recipeTemplates)
# repositoryMap (Default: [])
repositoryMap             bar.com                   https://dev.bar.com/conary/
repositoryMap             foo.com                   https://repo.foo.com/conary/
# repositoryUser (Default: []) (At `rbuild init': bar.com baruser barpassword, foo.com foouser foopassword)
# rmakePluginDirs (Default: /usr/share/rmake/plugins:~/.rmake/plugins.d) (At `rbuild init': /usr/share/rmake/plugins:~/.rmake/plugins.d)
# rmakeUrl (Default: None) (At `rbuild init': None)
# serverUrl (Default: None) (At `rbuild init': http://myrbuilder.foo)
# signatureKey (Default: None) (At `rbuild init': ASDF)
# signatureKeyMap (Default: []) (At `rbuild init': foo FDSA)
'''

        self.assertEqualWithDiff(dump, expected)

    def testPluginConfigurations(self):
        # Dump config file
        cfgFile = os.path.join(self.workDir, "rbuildrc")
        self.rbuildCfg.store(file(cfgFile, "w"))
        # Add a few sections
        with file(cfgFile, "a") as f:
            f.write("""
[edit]
name Marvin the Martian
device Illudium Q-36 Explosive Space Modulator
[dummy-section]
dummy-option-1 1
dummy-option-2 2
""")
        self.rbuildCfg.__init__(readConfigFiles=False, ignoreErrors=True)
        self.rbuildCfg.read(cfgFile)

        from rbuild import handle
        _C = rbuildcfg.cfg
        # Mock plugin loading so we can add some config options to one
        # of the plugins
        origLoadPluginFromFileName = handle.pluginloader.PluginManager.loadPluginFromFileName
        def mockedLoadPluginFromFileName(slf, dir, fileName, *args, **kwargs):
            plugin = origLoadPluginFromFileName(slf, dir, fileName, *args, **kwargs)
            if plugin and plugin.name == 'edit':
                class MyPluginConfiguration(plugin.PluginConfiguration):
                    name = (_C.CfgString, 'Jean Valjean')
                    device = _C.CfgString
                self.mock(plugin, 'PluginConfiguration', MyPluginConfiguration)
            return plugin
        self.mock(handle.pluginloader.PluginManager, 'loadPluginFromFileName',
                mockedLoadPluginFromFileName)
        handle = self.getRbuildHandle()
        handle.Edit.registerCommands()
        handle.Edit.initialize()

        section = handle.getConfig().getSection('edit')
        self.assertEquals(section.name, 'Marvin the Martian')
        self.assertEquals(section.device, 'Illudium Q-36 Explosive Space Modulator')
        # The section is passed by reference to the plugin
        self.assertTrue(handle.Edit.pluginCfg is section)

        # Dump the handler's config. It should include just the edit
        # section
        newCfg = cfgFile + '.new'
        handle.getConfig().writeToFile(newCfg)
        self.assertEquals(file(newCfg).read(), file(newCfg).read())

    def testCfgHttpUrlType(self):
        config = rbuildcfg.RbuildConfiguration()
        err = self.assertRaises(cfg.ParseError, config.configLine,
            'serverUrl http://:myrbuilder.foo')
        self.assertIn('valid http', str(err))
        err = self.assertRaises(cfg.ParseError, config.configLine,
            'serverUrl http://foo@myrbuilder.foo')
        self.assertIn('URL entries', str(err))
        config.configLine('serverUrl http://myrbuilder.foo:port')
        config.configLine('serverUrl http://myrbuilder.foo')
