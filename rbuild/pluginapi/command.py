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
command module.  Provides BaseCommand and CommandWithSubCommands superclasses
for use by plugins.

@var NO_PARAM: Command-line argument which takes no parameters; a flag
in the form C{--flag}
@var ONE_PARAM: Command-line argument which takes exactly one parameter,
in the forms C{--argument=value} or C{--argument value}
@var OPT_PARAM: Command-line argument which takes zero or one parameters,
in the forms C{--argument} or C{--argument=value} (note that this
form cannot take C{--argument value}
@var MULT_PARAM: Command-line argument which takes a multi-valued parameter,
in the forms C{--argument 'list of values'} or C{--argument='list of values'}
@var NORMAL_HELP: Command-line argument to include in the normal help
message (default)
@var VERBOSE_HELP: Command-line argument which should be shown only in
verbose help messages
@var SUPPRESS_HELP: Command-line argument which should never be shown in
any help messages
"""
from conary.lib import command
from conary.lib import log
from conary.lib import options
import optparse
import sys

from rbuild import errors


(NO_PARAM,  ONE_PARAM)  = (options.NO_PARAM, options.ONE_PARAM)
(OPT_PARAM, MULT_PARAM) = (options.OPT_PARAM, options.MULT_PARAM)
(NORMAL_HELP, VERBOSE_HELP, SUPPRESS_HELP)  = (
    options.NORMAL_HELP, options.VERBOSE_HELP, optparse.SUPPRESS_HELP)

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
            'quiet'              : (VERBOSE_HELP,
                                    "Quiet operation, intended for scripting"),
            'verbose'            : (VERBOSE_HELP,
                                    "Display more detailed information where"
                                    " available"),
            'stage'              : (VERBOSE_HELP, "Specify the stage to use"),
            'lsprof'             : SUPPRESS_HELP,
            }

    projectCommand = False
    stageCommand = False

    def addParameters(self, argDef):
        """
        Called by C{AbstractCommand}, this sets up default commands
        handled by all rbuild commands.  To extend this in a plugin,
        do::
            def addParameters(self, argDef):
                BaseCommand.addParameters(self, argDef)
                argDef['localflag'] = command.NO_PARAM
                argDef['localarg'] = command.ONE_PARAM
        The parameters will then be parsed and included in the C{argSet}
        provided to the plugin's C{runCommand} method.
        @param argDef: dictionary to which command flags are added
        """
        d = {}
        d["config"] = MULT_PARAM
        d["config-file"] = MULT_PARAM
        d["skip-default-config"] = NO_PARAM
        d["verbose"] = NO_PARAM
        d["quiet"] = NO_PARAM
        d["stage"] = ONE_PARAM
        d["lsprof"] = NO_PARAM
        argDef[self.defaultGroup] = d
        self.addLocalParameters(argDef)

    def addLocalParameters(self, argDef):
        """
        Stub method for doing special handling of arguments in plugins.
        Called by C{AbstractCommand}, this sets up default commands
        handled by all rbuild commands.  To extend this in a plugin,
        do::
            def addLocalParameters(self, argDef):
                argDef['localflag'] = command.NO_PARAM
                argDef['localarg'] = command.ONE_PARAM

        @param argDef: flags passed to the command
        @type argDef: dict
        """


    def processConfigOptions(self, rbuildConfig, cfgMap, argSet):
        """
        Add any configuration files mentioned on the command
        line to the contents of the config object, overriding
        any configuration data already found.  Then add any
        configuration items specified explicitly on the command
        line, overriding all configuration files, including any
        specified with C{--config-file}.
        @param rbuildConfig: rbuild configuration
        @param cfgMap: legacy option - ignore
        @param argSet: dictionary of option : value mapping based on options
        passed in at the command line.
        """ 

        configFileList = argSet.pop('config-file', [])

        for path in configFileList:
            rbuildConfig.read(path, exception=True)

        command.AbstractCommand.processConfigOptions(self, rbuildConfig,
                                                     cfgMap, argSet)
        rbuildConfig.quiet = argSet.get('quiet', False)
        if argSet.get('verbose', False):
            log.setVerbosity(log.DEBUG)
        self.processLocalConfigOptions(rbuildConfig, argSet)

    def processLocalConfigOptions(self, rbuildConfig, argSet):
        """
        Stub method for doing special handling of arguments in plugins,
        particularly arguments that affect C{rbuildConfig} or that
        require default handling.
        @param rbuildConfig: current rbuilder configuration
        @type rbuildConfig: C{rbuildcfg.RbuildConfiguration}
        @param argSet: flags passed to the command
        @type argSet: dict
        """
        # W0221: unused variables: Expected unused variables in a stub method.
        #pylint: disable-msg=W0221

    def runCommand(self, handle, argSet, args):
        """
        Stub method for running commands.  Should be replaced by subclasses.
        @param handle: rbuild handle object
        @param argSet: dictionary of flags passed to the command
        @param args: list of parameters passed (the first is the command name)
        """
        # W0221: unused variables: Expected unused variables in a stub method.
        #pylint: disable-msg=W0221
        raise NotImplementedError


class CommandWithSubCommands(BaseCommand):
    """
    Implements argument handling for commands with subcommands.

    Subcommands should be added via the registerSubCommand() class
    method.  The subCommands C{runCommand} method will be called with the
    same variables as there are in C{BaseCommand}.
    """
    paramHelp = '<subcommand> [options]'

    @classmethod
    def registerSubCommand(cls, name, subCommandClass, aliases=None):
        """
        Hook for registering subCommand classes.
        @param name: name for the subcommand.
        @param subCommandClass: BaseCommand subclass that implements the
        subcommand.
        @param aliases: list of command alias names.
        """
        if not '_subCommands' in cls.__dict__:
            cls._subCommands = {}
        if not '_usageSubCommands' in cls.__dict__:
            cls._usageSubCommands = {}
        if not aliases:
            aliases = []
        for alias in aliases:
            cls._subCommands[alias] = subCommandClass
        cls._subCommands[name] = subCommandClass
        cls._usageSubCommands[name] = subCommandClass
        subCommandClass.name = '%s %s' % (cls.commands[0], name)

    def addParameters(self, argDef):
        BaseCommand.addParameters(self, argDef)
        if not getattr(self, '_subCommands', None):
            self._subCommands = {}
        for cls in self._subCommands.values():
            cls().addLocalParameters(argDef)

    @classmethod
    def getSubCommandClass(cls, name):
        """
        Hook for fetching subCommand classes.
        @param name: name for the subcommand.
        @return: subCommand class or C{None}
        """
        if '_subCommands' in cls.__dict__ and name in cls._subCommands:
            return cls._subCommands[name]
        return None

    def runCommand(self, handle, argSet, args):
        #pylint: disable-msg=C0999
        # parameters documented by proxy
        """
        Takes the args list, determines the subcommand that is being called
        and calls that subcommand.

        Parameters are same as those in C{BaseCommand}
        """
        if not getattr(self, '_subCommands', None):
            return self.usage()
        if len(args) < 3:
            return self.usage()
        commandName = args[2]
        if commandName not in self._subCommands:
            return self.usage()
        subCommand = self._subCommands[commandName]()
        subCommand.setMainHandler(self.mainHandler)
        return subCommand.runCommand(handle, argSet, args[1:])

    def usage(self, rc=1):
        if not getattr(self, '_subCommands', None):
            self._subCommands = {}
        if not getattr(self, '_usageSubCommands', None):
            self._usageSubCommands = {}
        commandList = self._usageSubCommands.items()
        width = 0
        for commandName, commandClass in commandList:
            width = max(width, len(commandName))
        myClass = self.__class__
        if not myClass.description:
            myClass.description = myClass.__doc__
        if myClass.description is None:
            myClass.description = ''
        extraDescription = '\n\nSubcommands:\n'
        for commandName, commandClass in commandList:
            extraDescription += '     %-*s  %s\n' % (width, commandName,
                                                        commandClass.help)
        extraDescription += ("\n(Use '%s help %s <subcommand>'"
                             " for help on a subcommand)" \
                             % (self.mainHandler.name, self.commands[0]))
        self.parser = None
        oldDescription = myClass.description
        try:
            myClass.description += extraDescription
            BaseCommand.usage(self)
        finally:
            myClass.description = oldDescription

        return rc

    def subCommandUsage(self, subCommandName, errNo=1):
        if not self._subCommands.has_key(subCommandName):
            print "%s %s: no such subcommand: %s" % \
                   (self.mainHandler.name, self.commands[0], subCommandName)
            sys.exit(1)

        thisCommand = self._subCommands[subCommandName]()
        thisCommand.setMainHandler(self.mainHandler)
        params, _ = thisCommand.prepare()
        usage = '%s %s %s %s' % (self.mainHandler.name, '/'.join(self.commands),
                                 subCommandName, thisCommand.paramHelp)
        kwargs = self.mainHandler._getParserFlags(thisCommand)
        kwargs['defaultGroup'] = None
        parser = options._getParser(params, {}, usage=usage, **kwargs)
        parser.print_help()
        if log.getVerbosity() > log.INFO:
            print '(Use --verbose to get a full option listing)'
        return errNo


class ListCommand(BaseCommand):
    """
        Inherit for commands/sub-commands that lists or show things. Must
        include three class variables, and an optional fourth.

        Required:
            resource: name of the resource to list or showFieldMap
            listFields: tuple of fields to display in list
            listFieldMap: dictionary mapping fields to display options

        Optional:
            showFieldMap: dictionary mapping fields to display options

        Display options:
            display_name: alternative name to display for field, defaults to
                the field name. Eg. field_name_foo -> Field Name Foo
            accessor: a lambda that returns the value for field, defaults to
                lambda x: x.field_name
            hidden: never display this field, defaults to False
            verbose: do not display this field unless verbose is on, defaults
                to False

        Example:
            class FooListCommand(ListCommand):
                help = 'list foos'
                resource = 'foos'
                listFields = ('name', 'reversed_name')
                listFieldMap = dict(
                    reversed_name=dict(
                        display_name="Eman", accessor=lambda f: f.name[::-1]),
                    )
                showFieldMap = dict()
    """
    paramHelp = '[options] [id]*'
    listFieldMap = dict()

    def runCommand(self, handle, argSet, args):
        _, idList = self.requireParameters(args, allowExtra=True)
        if idList:
            self._show(handle, idList)
        else:
            self._list(handle)

    def _fieldNameToDisplayName(self, field, mapping):
            fdict = mapping.get(field, dict())
            display_name = fdict.get('display_name')
            if display_name is None:
                # use the element name
                display_name = ' '.join(
                    w[0].upper() + w[1:] for w in field.split('_'))
            return display_name

    def _getResourceData(self, resource, fields, mapping, row_major=True):
        for field in fields:
            fdict = mapping.get(field, dict())
            if fdict.get('hidden', False) or fdict.get('verbose', False):
                continue
            accessor = fdict.get('accessor', lambda i: getattr(i, field))
            try:
                value = accessor(resource)
            except AttributeError:
                # summary views can cause cache poisoning which manifests as
                # AttributeErrors; refresh the resource and try again
                resource.refresh()
                value = accessor(resource)

            if row_major:
                yield value
            else:
                display_name = self._fieldNameToDisplayName(field, mapping)
                yield (display_name, value)

    def _list(self, handle, *args, **kwargs):
        headers = tuple(self._fieldNameToDisplayName(field, self.listFieldMap)
                        for field in self.listFields)

        resources = handle.getPlugin(self.resource).list(*args, **kwargs)
        if resources:
            data = []
            for resource in resources:
                data.append(tuple(self._getResourceData(
                    resource, self.listFields, self.listFieldMap)))
            handle.ui.writeTable(data, headers)
        else:
            handle.ui.warning('No %s found' % self.resource)
        return resources

    def _show(self, handle, idList):
        if not hasattr(self, 'showFieldMap'):
            raise errors.PluginError(
                "'%s' does not support showing specific resources" %
                self.resource)
        for resourceId in idList:
            resource = handle.getPlugin(self.resource).show(resourceId)
            if resource:
                showFieldList = list(set(resource.elements
                                         + self.showFieldMap.keys()))
                showFieldList.sort()
                handle.ui.writeTable(list(self._getResourceData(
                    resource,
                    showFieldList,
                    self.showFieldMap,
                    row_major=False,
                    )))
                handle.ui.write()
            else:
                handle.ui.warning(
                    "No %s found with id '%s'", self.resource, resourceId)

