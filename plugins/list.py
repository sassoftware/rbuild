#
# Copyright (c) SAS Institute, Inc.
#

from rbuild import pluginapi
from rbuild.pluginapi import command


class ListCommand(command.CommandWithSubCommands):
    help = 'List objects associated with the rbuilder'
    commands = ['list', 'query']


class List(pluginapi.Plugin):
    name = 'list'

    def registerCommands(self):
        self.handle.Commands.registerCommand(ListCommand)
