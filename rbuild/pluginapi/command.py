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
from conary.lib import options

(NO_PARAM,  ONE_PARAM)  = (options.NO_PARAM, options.ONE_PARAM)
(OPT_PARAM, MULT_PARAM) = (options.OPT_PARAM, options.MULT_PARAM)
(NORMAL_HELP, VERBOSE_HELP)  = (options.NORMAL_HELP, options.VERBOSE_HELP)

class BaseCommand(command.AbstractCommand):

    docs = {'config'             : (VERBOSE_HELP,
                                    "Set config KEY to VALUE", "'KEY VALUE'"),
            'config-file'        : (VERBOSE_HELP,
                                    "Read PATH config file", "PATH"),
            'skip-default-config': (VERBOSE_HELP,
                                    "Don't read default configs"),
            'verbose'            : (VERBOSE_HELP,
                                "Display more detailed information where available") }

    def addParameters(self, argDef):
        d = {}
        d["config"] = MULT_PARAM
        d["config-file"] = MULT_PARAM
        d["skip-default-config"] = NO_PARAM
        d["verbose"] = NO_PARAM
        argDef[self.defaultGroup] = d

    def processConfigOptions(self, rbuildConfig, cfgMap, argSet):
        """
            Manage any config maps we've set up, converting 
            assigning them to the config object.
        """ 

        configFileList = argSet.pop('config-file', [])

        for path in configFileList:
            rbuildConfig.read(path, exception=True)

        for (arg, data) in cfgMap.items():
            cfgName, paramType = data[0:2]
            value = argSet.pop(arg, None)
            if value is not None:
                if arg.startswith('no-'):
                    value = not value

                rbuildConfig.configLine("%s %s" % (cfgName, value))

        for line in argSet.pop('config', []):
            rbuildConfig.configLine(line)

        if argSet.pop('verbose', False):
            log.setVerbosity(log.DEBUG)


class CommandWithSubCommands(BaseCommand):
    @classmethod
    def registerSubCommand(myClass, name, class_):
        if not '_subCommands' in myClass.__dict__:
            myClass._subCommands = {}
        myClass._subCommands[name] = class_

    def runCommand(self, client, cfg, argSet, args):
        if not hasattr(self, '_subCommands'):
            self.usage()
        commandName = args[1]
        if commandName not in self._subCommands:
            return self.usage()
        class_ = self._subCommands[commandName]
        return class_().runCommand(client, cfg, argSet, args[2:])
