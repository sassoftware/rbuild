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
Built in "help" command
"""

import sys

from rbuild.pluginapi.command import BaseCommand

class HelpCommand(BaseCommand):
    """
    Displays help about this program or commands within the program.
    """
    commands = ['help']
    help = 'Display help information'
    commandGroup = 'Information Display'

    # configuration setup is not required to run the help command
    requireConfig = False

    def runCommand(self, handle, argSet, args):
        #pylint: disable-msg=C0999
        # interface implementation does not require argument documentation
        """
        Runs the help command, displaying either general help including
        a list of commonly-used command, or help on a specific command.
        """
        # W0613: unused variables handle, argSet for implementing interface
        #pylint: disable-msg=W0613
        command, subCommands = self.requireParameters(args, allowExtra=True,
                                                      maxExtra=2)
        if subCommands:
            command = subCommands[0]
            commands = self.mainHandler.getSupportedCommands()
            if not command in commands:
                print "%s: no such command: '%s'" % (self.mainHandler.name,
                                                     command)
                sys.exit(1)
            if len(subCommands) == 2:
                commands[command].subCommandUsage(subCommands[1])
            else:
                commands[command].usage()
            return 0
        else:
            self.mainHandler.usage(showAll=True)
            return 0
