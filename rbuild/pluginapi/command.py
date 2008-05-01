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
from conary.lib import log
from conary.lib import options

"""
@var NO_PARAM: Command-line argument which takes no parameters; a flag
in the form C{--flag}
@var ONE_PARAM: Command-line argument which takes exactly one parameter,
in the forms C{--argument=value} or C{--argument value}}
@var OPT_PARAM: Command-line argument which takes zero or one parameters,
in the forms C{--argument} or C{--argument=value} (note that this
form cannot take C{--argument value}
@var MULT_PARAM: Command-line argument which takes a multi-valued parameter,
in the forms C{--argument 'list of values'} or C{--argument='list of values'}
@var NORMAL_HELP: Command-line argument to include in the normal help
message (default)
@var VERBOSE_HELP: Command-line argument which should be shown only in
verbose help messages
"""

(NO_PARAM,  ONE_PARAM)  = (options.NO_PARAM, options.ONE_PARAM)
(OPT_PARAM, MULT_PARAM) = (options.OPT_PARAM, options.MULT_PARAM)
(NORMAL_HELP, VERBOSE_HELP)  = (options.NORMAL_HELP, options.VERBOSE_HELP)

class BaseCommand(command.AbstractCommand):
    """
    Implements the core argument handling for all rbuild plugins.
    """

    docs = {'config'             : (VERBOSE_HELP,
                                    "Set config KEY to VALUE", "'KEY VALUE'"),
            'config-file'        : (VERBOSE_HELP,
                                    "Read PATH config file", "PATH"),
            'skip-default-config': (VERBOSE_HELP,
                                    "Don't read default configs"),
            'verbose'            : (VERBOSE_HELP,
                                    "Display more detailed information where"
                                    " available") }

    def addParameters(self, argDef):
        """
        Called by C{AbstractCommand}, this sets up default commands
        handled by all rbuild commands.  To extend this in a plugin,
        do::
            argDef = {}
            BaseCommand.addParameters(self, argDef)
            argDef['localflag'] = command.NO_PARAM
            argDef['localarg'] = command.ONE_PARAM
        """
        d = {}
        d["config"] = MULT_PARAM
        d["config-file"] = MULT_PARAM
        d["skip-default-config"] = NO_PARAM
        d["verbose"] = NO_PARAM
        argDef[self.defaultGroup] = d

    def processConfigOptions(self, rbuildConfig, cfgMap, argSet):
        """
        Add any configuration files mentioned on the command
        line to the contents of the config object, overriding
        any configuration data already found.  Then add any
        configuration items specified explicitly on the command
        line, overriding all configuration files, including any
        specified with C{--config-file}.
        """ 

        configFileList = argSet.pop('config-file', [])

        for path in configFileList:
            rbuildConfig.read(path, exception=True)

        if argSet.pop('verbose', False):
            log.setVerbosity(log.DEBUG)
        return command.AbstractCommand.processConfigOptions(self, rbuildConfig,
                                                            cfgMap, argSet)


    def runCommand(self, client, cfg, argSet, args):
        #pylint: disable-msg=W0221
        # we're overriding this method for our program's needs
        raise NotImplementedError


class CommandWithSubCommands(BaseCommand):
    @classmethod
    def registerSubCommand(cls, name, subCommandClass):
        if not '_subCommands' in cls.__dict__:
            cls._subCommands = {}
        cls._subCommands[name] = subCommandClass

    def runCommand(self, client, cfg, argSet, args):
        if not hasattr(self, '_subCommands'):
            self.usage()
        commandName = args[1]
        if commandName not in self._subCommands:
            return self.usage()
        subCommandClass = self._subCommands[commandName]
        return subCommandClass().runCommand(client, cfg, argSet, args[2:])
