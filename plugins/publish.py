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

class PublishCommand(command.BaseCommand):
    '''
    Publishes a release of images built from the current stage.
    '''
    help = 'Publish image release'
    paramHelp = '[release ID]*'
    docs = { 'no-mirror' : 'do not mirror the published release',
           }

    commands = ['publish']

    def addLocalParameters(self, argDef):
        argDef['no-mirror'] = command.NO_PARAM

    #pylint: disable-msg=R0201,R0903
    # could be a function, and too few public methods
    def runCommand(self, handle, argSet, args):
        mirror = not argSet.pop('no-mirror', False)
        _, releaseIds = self.requireParameters(args, allowExtra=True)
        if releaseIds:
            releaseIds = [int(x) for x in releaseIds]
        else:
            releaseId = handle.Publish.getReleaseId()
            if not releaseId:
                raise errors.PluginError(
                    'No release Id found to publish for current stage')
            releaseIds = [releaseId]
        for releaseId in releaseIds:
            handle.Publish.publishRelease(releaseId, mirror)

class Publish(pluginapi.Plugin):
    name = 'publish'

    def registerCommands(self):
        self.handle.Commands.registerCommand(PublishCommand)

    def getReleaseId(self):
        return self.handle.productStore.getStageReleaseId()

    def publishRelease(self, releaseId, shouldMirror):
        self.handle.facade.rbuilder.publishRelease(releaseId, shouldMirror)
        self.handle.ui.write('Published release %s' % releaseId)
