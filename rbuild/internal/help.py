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

from conary.lib import options
from rbuild.pluginapi.command import BaseCommand

class HelpCommand(BaseCommand):
    commands = ['help']
    help = 'Display help information'
    commandGroup = 'Information Display'

    def runCommand(self, rbClient, cfg, argSet, args):
        command, subCommands = self.requireParameters(args, allowExtra=True,
                                                      maxExtra=1)
        if subCommands:
            command = subCommands[0]
            commands = self.mainHandler._supportedCommands
            if not command in commands:
                print "%s: no such command: '%s'" % (self.mainHandler.name,
                                                     command)
                sys.exit(1)
            commands[command].usage()
        else:
            self.mainHandler.usage(showAll=True)
            return 0
