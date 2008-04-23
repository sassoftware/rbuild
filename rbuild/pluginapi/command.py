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

from conary.lib import command

class BaseCommand(command.AbstractCommand):
    def requireParameters(self, args, expected=None, allowExtra=False,
                          appendExtra=False, maxExtra=None):
        args = args[1:] # cut off argv[0]
        command = repr(args[0])
        if isinstance(expected, str):
            expected = [expected]
        if expected is None:
            expected = ['command']
        else:
            expected = ['command'] + expected
        if expected:
            missing = expected[len(args):]
            if missing:
                raise errors.BadParameters('%s missing %s command'
                                           ' parameter(s): %s' % (
                                            command, len(missing),
                                            ', '.join(missing)))
        extra = len(args) - len(expected)
        if not allowExtra and not appendExtra:
            maxExtra = 0
        if maxExtra is not None and extra > maxExtra:
            if maxExtra:
                numParams = '%s-%s' % (len(expected)-1,
                                       len(expected) + maxExtra - 1)
            else:
                 numParams = '%s' % (len(expected)-1)
            raise errors.BadParameters('%s takes %s arguments, received %s' % (command, numParams, len(args)-1))

        if appendExtra:
            # final parameter is list 
            return args[:len(expected)-1] + [args[len(expected)-1:]]
        elif allowExtra:
            return args[:len(expected)] + [args[len(expected):]]
        else:
            return args


class CommandWithSubCommands(BaseCommand):
    @classmethod
    def registerSubCommand(myClass, name, class_):
        if not '_subCommands' in myClass.__dict__:
            myClass._subCommands = {}
        myClass._subCommands[name] = class_

    def runCommand(self, client, cfg, argSet, args):
        if hasattr(self, '_subCommands'):
            self.usage()
        commandName = args[1]
        if commandName not in self._subCommands:
            return self.usage()
        class_ = self._subCommands[commandName]
        return class_().runCommand(client, cfg, argSet, args[2:])
