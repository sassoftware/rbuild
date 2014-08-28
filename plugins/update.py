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
Update packages and product definition source troves managed by Conary
"""
import os

from rbuild import errors
from rbuild import pluginapi
from rbuild.productstore.decorators import requiresStage

class UpdateCommand(pluginapi.command.CommandWithSubCommands):
    """
    Updates source directories based on working directory
    """
    commands = ['update']
    help = 'Update working directories from repository'
    def runCommand(self, handle, argSet, args):
        """
        Process the command line provided for this plugin
        @param handle: context handle
        @type handle: rbuild.handle.RbuildHandle
        @param argSet: dictionary of flags passed to the command
        @param args: command-line arguments
        @type args: iterable
        """
        if len(args) == 2:
            handle.Update.updateByCurrentDirectory()
        else:
            pluginapi.command.CommandWithSubCommands.runCommand(self,
                handle, argSet, args)
        return None

class UpdateProductCommand(pluginapi.command.BaseCommand):
    """
    Updates product directory relative to working directory
    """
    help = 'Update product directory relative to working directory'
    def runCommand(self, handle, _, args):
        #pylint: disable-msg=C0999,W0613
        #can't have two args both called _ to make them be ignored
        """
        Process the command line provided for this plugin
        @param handle: context handle
        @type handle: rbuild.handle.RbuildHandle
        """
        handle.productStore.update()
        return None


class UpdatePackagesCommand(pluginapi.command.BaseCommand):
    """
    Updates all packages in all stages
    """
    help = 'Updates all packages in all stages'
    def runCommand(self, handle, _, args):
        #pylint: disable-msg=C0999,W0613
        #can't have two args both called _ to make them be ignored
        """
        Process the command line provided for this plugin
        @param handle: context handle
        @type handle: rbuild.handle.RbuildHandle
        """
        handle.Update.updateAllStages()
        return None


class UpdateStageCommand(pluginapi.command.BaseCommand):
    """
    Updates all packages in stage
    """
    help = 'Updates all packages in current or named stage(s)'
    paramHelp = '[stagename]*'
    def runCommand(self, handle, _, args):
        #pylint: disable-msg=C0999,W0613
        #can't have two args both called _ to make them be ignored
        """
        Process the command line provided for this plugin
        @param handle: context handle
        @type handle: rbuild.handle.RbuildHandle
        @param args: command-line arguments
        @type args: iterable
        """
        args = args[2:]
        if args:
            handle.Update.updateStages(args)
        else:
            handle.Update.updateCurrentStage()
        return None


class UpdateAllCommand(pluginapi.command.BaseCommand):
    """
    Updates all contents of checkout, regardless of current directory
    """
    help = 'Updates all checkout contents, from any directory'
    def runCommand(self, handle, _, args):
        #pylint: disable-msg=C0999,W0613
        #can't have two args both called _ to make them be ignored
        """
        Process the command line provided for this plugin
        @param handle: context handle
        @type handle: rbuild.handle.RbuildHandle
        """
        handle.productStore.update()
        handle.Update.updateAllStages()
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

    def initialize(self):
        cmd = self.handle.Commands.getCommandClass('update')
        cmd.registerSubCommand('product', UpdateProductCommand)
        cmd.registerSubCommand('packages', UpdatePackagesCommand)
        cmd.registerSubCommand('stage', UpdateStageCommand)
        cmd.registerSubCommand('all', UpdateAllCommand)

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

    @requiresStage
    def updateCurrentStage(self):
        """
        Update all source packages in the current stage in the current product.
        """
        stageName = self.handle.productStore.getActiveStageName()
        self.updateStages([stageName])

    def updateStages(self, stageNames):
        """
        Update all source packages in all listed stages in the current product.
        @param stageNames: names of stages to update
        @type stageNames: list of strings
        """
        productStore = self.handle.productStore
        for stageName in stageNames:
            for checkoutDict in productStore.getEditedRecipeDicts(stageName):
                for packageDir in sorted(checkoutDict.values()):
                    if not os.path.isdir(packageDir):
                        packageDir = os.path.dirname(packageDir)
                    self.handle.facade.conary.updateCheckout(packageDir)

    def updateCurrentDirectory(self):
        """
        Update the contents of the source package in the current directory
        """
        self.handle.facade.conary.updateCheckout(os.getcwd())
