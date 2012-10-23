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
