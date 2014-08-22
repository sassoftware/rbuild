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


from rbuild import pluginapi
from rbuild.decorators import requiresProduct
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

    @requiresProduct
    def buildPlatform(self):
        conaryClient = self.handle.facade.conary._getConaryClient()
        self.handle.product.savePlatformToRepository(conaryClient)
        self.handle.productStore.checkoutPlatform()
        self.handle.ui.info('New platform definition created.')
