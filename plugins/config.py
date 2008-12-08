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
import os

from rbuild import pluginapi
from rbuild.pluginapi import command

class ConfigCommand(command.BaseCommand):
    commands = ['config']
    help = 'Print the rbuild configuration'

    # configuration setup is not required to run the help command
    requireConfig = False

    def addLocalParameters(self, argSet):
        argSet['ask'] = command.NO_PARAM

    def runCommand(self, handle, argSet, _):
        if argSet.pop('ask', False):
            handle.Config.updateConfig()
        else:
            handle.Config.displayConfig()


class Config(pluginapi.Plugin):
    name = 'config'

    def registerCommands(self):
        self.handle.Commands.registerCommand(ConfigCommand)

    def displayConfig(self, hidePasswords=True, prettyPrint=True):
        """
        Display the current build configuration for this helper.

        @param hidePasswords: If C{True} (default), display C{<password>}
        instead of the literal password in the output.
        @param prettyPrint: If C{True} (default), print output in
        human-readable format that may not be parsable by a config reader.
        If C{False}, the configuration output should be valid as input.
        """
        cfg = self.handle.getConfig()
        cfg.setDisplayOptions(hidePasswords=hidePasswords,
                              prettyPrint=prettyPrint)
        cfg.display()

    @staticmethod
    def isComplete(cfg):
        for cfgItem in ['serverUrl', 'name', 'contact', 'user']:
            if not cfg[cfgItem]:
                return False
        return True

    def initializeConfig(self, cfg=None):
        if cfg is None:
            cfg = self.handle.getConfig()
        ui = self.handle.ui
        ui.write('''\
********************************************************
Welcome to rBuild!  Your configuration is incomplete.
Please answer the following questions to begin using rBuild:
''')

        self.updateConfig(cfg)

        ui.write("rBuild configuration complete.  To rerun this"
                 " configuration test run rbuild config --ask,"
                 " or simply edit ~/.rbuildrc.")
        ui.write('')
        ui.write("You should now begin working with a product by running"
                   " 'rbuild init <short name> <version>'")

    def updateConfig(self, cfg=None):
        if cfg is None:
            cfg = self.handle.getConfig()
        ui = self.handle.ui
        validateUrl = self.handle.facade.rbuilder.validateUrl
        cfg.serverUrl = ui.getResponse('URL to use to contact rBuilder'
                                       ' (start with http:// or https://)',
                                       validationFn=validateUrl,
                                       default=cfg.serverUrl)
        ui.write('rBuilder contacted ok.')
        if cfg.user:
            defaultUser = cfg.user[0]
            defaultPassword = cfg.user[1]
        else:
            defaultUser = defaultPassword = None

        user =  ui.getResponse('Your rbuilder user name',
                               default=defaultUser)
        passwd = ui.getPassword('Your rbuilder password',
                                default=defaultPassword)
        cfg.user = (user, passwd)
        cfg.name = ui.getResponse('Name to display when committing',
                                  default=cfg.name)
        cfg.contact = ui.getResponse('Contact - usually email or url',
                                     default=cfg.contact)
        if 'HOME' in os.environ:
            oldumask = os.umask(077)
            try:
                cfg.writeToFile(os.environ['HOME'] + '/.rbuildrc')
            finally:
                os.umask(oldumask)

