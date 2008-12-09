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
"""
Build command, all build subcommands should register with this command using
the C{registerSubCommand}
"""

from rbuild import pluginapi
from rbuild import errors
from rbuild.pluginapi import command

class OutdatedProductDefinitionError(errors.PluginError):
    '''
    Raised to indicate that the product definition in use is out of date
    with respect to the repository, in cases where this is an error.
    '''

class BuildCommand(command.CommandWithSubCommands):
    """
    Build commands for building the various components of a product.
    """
    help = 'Build the various components of a product'
    commands = ['build']


class Build(pluginapi.Plugin):
    name = 'build'

    def registerCommands(self):
        self.handle.Commands.registerCommand(BuildCommand)

    def watchAndCommitJob(self, jobId):
        return self.handle.facade.rmake.watchAndCommitJob(jobId)

    def watchJob(self, jobId):
        return self.handle.facade.rmake.watchJob(jobId)

    def warnIfOldProductDefinition(self, actionName, display=True):
        '''
        Warns if there are newer commits to the product-definition
        in the repository that have not been applied to the local
        checkout.
        @param actionName: String naming the action being taken; shown
        in informational messages to the user
        @param display: (True) Prints the contents of the differences
        @raise OutdatedProductDefinitionError: If user requests to
        abort the action
        '''
        if not hasattr(self.handle.productStore, 'getProductDefinitionDirectory'):
            # This is not a checkout; we cannot test
            return

        proddefDir = self.handle.productStore.getProductDefinitionDirectory()
        productName = self.handle.product.getProductName()
        conaryfacade = self.handle.facade.conary

        newerVersions = conaryfacade._getNewerRepositoryVersions(proddefDir)
        if not newerVersions:
            return

        ui = self.handle.ui
        ui.write('The local copy of the %s product definition is out of date',
                 productName)
        if display:
            ui.write('The following changes are committed to the repository,')
            ui.write('but are not included in your local copy:')
            ui.write()
            for line in conaryfacade.iterRepositoryDiff(proddefDir,
                                                        newerVersions[-1]):
                ui.write(line)
            ui.write()
            ui.write('The following change messages describe the changes'
                     ' just displayed:')
            for line in conaryfacade.getCheckoutLog(proddefDir,
                                                    versionList=newerVersions):
                ui.write(line)
            ui.write()

        ui.write('If any of the newer changes may affect you, answer "no",')
        ui.write('and run the command "rbuild update product" to update')
        ui.write('your local copy of the product definition.')
        ui.write()
        response = ui.getResponse('Proceed with %s, ignoring differences in'
                                  ' product definition?' %actionName,
                                  default='Y')

        if response and response[0] not in ('y', 'Y'):
            raise OutdatedProductDefinitionError(
                '%s product definition out of date' %productName)
