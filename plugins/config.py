#
# Copyright (c) 2008 rPath, Inc.
#
# This program is distributed under the terms of the Common Public License,
# version 1.0. A copy of this license should have been distributed with this
# source file in a file called LICENSE. If it is not present, the license
# is always available at http://www.rpath.com/permanent/licenses/CPL-1.0.
#
# This program is distributed in the hope that it will be useful, but
# without any warranty; without even the implied warranty of merchantability
# or fitness for a particular purpose. See the Common Public License for
# full details.
#

from rbuild import pluginapi
from rbuild.pluginapi import command

class ConfigCommand(command.BaseCommand):
    commands = ['config']
    def runCommand(self, handle, cfg, argSet, args):
        # W0613: Unused variables
        # pylint: disable-msg=W0613
        handle.Config.displayConfig(handle)


class Config(pluginapi.Plugin):
    name = 'config'

    def registerCommands(self, handle):
        handle.Commands.registerCommand(ConfigCommand)

    def displayConfig(self, handle, hidePasswords=True, prettyPrint=True):
        """
        Display the current build configuration for this helper.

        @param hidePasswords: If C{True} (default), display C{<password>}
        instead of the literal password in the output.
        @param prettyPrint: If C{True} (default), print output in
        human-readable format that may not be parsable by a config reader.
        If C{False}, the configuration output should be valid as input.
        """
        # R0201: method could be a function.  No it couldn't.
        # pylint: disable-msg=R0201
        cfg = handle.getConfig()
        cfg.setDisplayOptions(hidePasswords=hidePasswords,
                              prettyPrint=prettyPrint)
        cfg.display()
