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
