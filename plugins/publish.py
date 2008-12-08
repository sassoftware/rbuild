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

class PublishCommand(command.BaseCommand):
    '''
    Publishes a release of images built from the current stage.
    '''
    help = 'Publish image release.'
    paramHelp = ''
    docs = { 'no-mirror' : 'do not mirror the published release',
           }

    commands = ['publish']

    def addLocalParameters(self, argDef):
        argDef['no-mirror'] = command.NO_PARAM

    #pylint: disable-msg=R0201,R0903
    # could be a function, and too few public methods
    def runCommand(self, handle, argSet, args):
        mirror = not argSet.pop('no-commit', False)
        releaseId = handle.Publish.getReleaseId()
        if not releaseId:
            handle.ui.writeError(
                'No release Id found to publish for current stage')
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
