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
