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

from rbuild import pluginapi
from rbuild.pluginapi import command

class BuildPlatformCommand(command.BaseCommand):
    help = 'Create a platform usable by others from this product'

    #pylint: disable-msg=R0201,R0903
    # could be a function, and too few public methods
    def runCommand(self, handle, _, args):
        # no allowed parameters
        self.requireParameters(args)
        handle.BuildPlatform.buildPlatform()


class BuildPlatform(pluginapi.Plugin):
    name = 'buildplatform'

    def initialize(self):
        self.handle.Commands.getCommandClass('build').registerSubCommand(
                                        'platform', BuildPlatformCommand)

    def buildPlatform(self):
        conaryClient = self.handle.facade.conary._getConaryClient()
        self.handle.product.savePlatformToRepository(conaryClient)
        self.handle.productStore.checkoutPlatform()
        self.handle.ui.info('New platform definition created.')
