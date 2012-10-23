#
# Copyright (c) rPath, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
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

    def initialize(self):
        for plugin in self.plugins:
            plugin.initialize()

def getPlugins(argv, pluginDirs, disabledPlugins=None):
    # TODO: look for plugin-related options in argv, perhaps with our
    # own lenient parser.
    # until then, ignore unused argv argument
    # pylint: disable-msg=W0613
    pluginMgr = PluginManager(pluginDirs, disabledPlugins,
                              pluginPrefix=PLUGIN_PREFIX)
    pluginMgr.loadPlugins()
    return pluginMgr
