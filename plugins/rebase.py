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
rebase command and related utilities.
"""
from rbuild.pluginapi import command
from rbuild import pluginapi

class RebaseCommand(command.BaseCommand):
    help = 'Rebases this product on the latest version of its platform'

    commands = ['rebase']

    def runCommand(self, handle, _, args):
        #disallow extra parameters
        _, extra = self.requireParameters(args, allowExtra=True, maxExtra=1)
        if extra:
            label = extra[0]
        else:
            label = None
        handle.Rebase.rebaseProduct(label)

class Rebase(pluginapi.Plugin):
    name = 'rebase'

    def registerCommands(self):
        self.handle.Commands.registerCommand(RebaseCommand)

    def rebaseProduct(self, label=None):
        handle = self.handle
        conaryClient = handle.facade.conary._getConaryClient()
        handle.product.rebase(conaryClient, label=label)
        handle.product.saveToRepository(conaryClient)
        handle.productStore.update()
        platformSource = handle.product.getPlatformSourceTrove()
        handle.ui.info(
         'Now using latest platform from %s' % (platformSource,))
