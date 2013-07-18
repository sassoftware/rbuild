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


from rmake.lib import pluginlib

#: C{PLUGIN_PREFIX} is a synthetic namespace which plugins use to
#: refer to each other: C{from rbuild_plugins import ...}
PLUGIN_PREFIX = 'rbuild_plugins'

class PluginManager(pluginlib.PluginManager):
    #pylint: disable-msg=R0904
    # "the creature can't help its ancestry"

    def registerCommands(self, main, handle):
        for plugin in self.plugins:
            plugin.registerCommands()
        for command in handle.Commands.getAllCommandClasses():
            main.registerCommand(command)

    def registerFacade(self, handle):
        for plugin in self.plugins:
            plugin.registerFacade(handle)

    def initialize(self):
        for plugin in self.plugins:
            plugin.initialize()

    def addPluginConfigurationClasses(self, cfg):
        for plugin in self.plugins:
            cfg.addPluginConfigHandler(plugin.name, plugin.PluginConfiguration)

    def setPluginConfigurations(self, cfg):
        for plugin in self.plugins:
            plugin.pluginCfg = cfg.getSection(plugin.name)

def getPlugins(argv, pluginDirs, disabledPlugins=None):
    # TODO: look for plugin-related options in argv, perhaps with our
    # own lenient parser.
    # until then, ignore unused argv argument
    # pylint: disable-msg=W0613
    pluginMgr = PluginManager(pluginDirs, disabledPlugins,
                              pluginPrefix=PLUGIN_PREFIX)
    pluginMgr.loadPlugins()
    return pluginMgr
