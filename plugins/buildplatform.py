#
# Copyright (c) rPath, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
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
