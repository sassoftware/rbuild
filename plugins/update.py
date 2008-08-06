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
Update packages and product definition source troves managed by Conary
"""
import os

from rbuild import errors
from rbuild import pluginapi

class UpdateCommand(pluginapi.command.BaseCommand):
    """
    Updates source directories
    """
    commands = ['update']
    help = 'Update working directories from repository'
    # FIXME: help for optional subcommands: product packages stage all
    def runCommand(self, handle, _, args):
        """
        Process the command line provided for this plugin
        @param handle: context handle
        @type handle: rbuild.handle.RbuildHandle
        @param args: command-line arguments
        @type args: iterable
        """
        if len(args) == 2:
            handle.Update.updateByCurrentDirectory()
        else:
            target = self.requireParameters(args,
                ['[product|packages|stage|all]'],
                allowExtra=True,
                appendExtra=True)[1:][0]
            target, extra = target[0], target[1:]
            if target not in ('product', 'packages', 'stage', 'all'):
                raise errors.BadParameters('update unrecognized command %s'
                                           %target)
            if target in ('product', 'all'):
                handle.productStore.update()
            if target in ('packages', 'all'):
                handle.Update.updateAllStages()
            elif target == 'stage':
                if extra:
                    handle.Update.updateStages(extra)
                else:
                    handle.Update.updateCurrentStage()
        return None



class Update(pluginapi.Plugin):
    """
    Update plugin
    """
    name = 'update'

    def registerCommands(self):
        """
        Register the command-line handling portion of the update plugin.
        """
        self.handle.Commands.registerCommand(UpdateCommand)

    def updateByCurrentDirectory(self):
        """
        Update whatever source checkout directory is appropriate for
        the current directory.
        """
        if os.path.exists('CONARY'):
            self.updateCurrentDirectory()
        elif os.path.exists('.rbuild'):
            self.handle.productStore.update()
        else:
            self.updateCurrentStage()

    def updateAllStages(self):
        """
        Update all source packages in all stages in the current product.
        """
        self.handle.Update.updateStages(
            self.handle.productStore.iterStageNames())

    def updateCurrentStage(self):
        """
        Update all source packages in the current stage in the current product.
        """
        stageName = self.handle.productStore.getActiveStageName()
        if not stageName:
            raise errors.RbuildError('Could not find current stage')
        self.updateStages([stageName])

    def updateStages(self, stageNames):
        """
        Update all source packages in all listed stages in the current product.
        @param stageNames: names of stages to update
        @type stageNames: list of strings
        """
        productStore = self.handle.productStore
        for stageName in stageNames:
            for packageDir in sorted(productStore.getEditedRecipeDicts(
                stageName)[0].values()):
                self.handle.facade.conary.updateCheckout(packageDir)

    def updateCurrentDirectory(self):
        """
        Update the contents of the source package in the current directory
        """
        self.handle.facade.conary.updateCheckout('.')
