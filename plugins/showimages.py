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
from rbuild import errors
from rbuild import pluginapi
from rbuild.pluginapi import command

class ShowImagesCommand(command.BaseCommand):
    help = 'show latest image build'

    #pylint: disable-msg=R0201,R0903,W0613
    # could be a function, and too few public methods,unused arguments
    def runCommand(self, handle, argSet, args):
        self.requireParameters(args)
        handle.ShowImages.showImageStatus()

class ShowImages(pluginapi.Plugin):
    name = 'showimages'

    def initialize(self):
        self.handle.Commands.getCommandClass('show').registerSubCommand(
                                            'images', ShowImagesCommand)

    def showImageStatus(self):
        jobId = self.handle.productStore.getImageJobId()
        if not jobId:
            raise errors.PluginError('No images have been built'
                                     ' in this environment')
        self.handle.Show.showJobStatus(jobId)
        return jobId
