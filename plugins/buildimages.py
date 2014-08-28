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
from rbuild.productstore.decorators import requiresStage
from rbuild.pluginapi import command

class BuildImagesCommand(command.BaseCommand):
    '''
    Builds specified images for the current stage.  If no images are specified,
    builds all images defined by the product.  
    '''
    help = 'Build images for this stage'
    paramHelp = '[image name]*'
    docs = {'no-watch' : 'do not wait for the job to complete',
           }

    def addLocalParameters(self, argDef):
        argDef['no-watch'] = command.NO_PARAM

    #pylint: disable-msg=R0201,R0903
    # could be a function, and too few public methods
    @requiresStage
    def runCommand(self, handle, argSet, args):
        watch = not argSet.pop('no-watch', False)
        _, imageNames = self.requireParameters(args, allowExtra=True)
        if imageNames == []:
            imageNames = None

        buildIds = handle.BuildImages.buildImages(imageNames)
        handle.productStore.setImageJobIds(buildIds)
        if watch:
            ok = handle.facade.rbuilder.watchImages(buildIds)
            if not ok:
                return 10
            for buildId in buildIds:
                handle.BuildImages.printImageUrlsForBuild(buildId)
        else:
            for buildId in buildIds:
                print buildId


class BuildImages(pluginapi.Plugin):
    name = 'buildimages'

    def initialize(self):
        self.handle.Commands.getCommandClass('build').registerSubCommand(
                                    'images', BuildImagesCommand)

    def buildImages(self, names=None):
        '''
        Build all images, or all images named in C{names}
        @param names: (C{None}) names of images to build (build all
        images if C{None})
        @type names: list of strings
        @return: job identifier
        @rtype: int
        '''
        self.handle.Build.warnIfOldProductDefinition('building images')
        buildIds = self.handle.facade.rbuilder.buildAllImagesForStage(
                buildNames=names)
        return buildIds

    def printImageUrlsForBuild(self, buildId):
        '''
        Print (at info level) tab-separated data for a build:
        - buildId
        - base file name
        - fileId
        - download URL
        '''
        for build in self.handle.facade.rbuilder.getBuildFiles(buildId):
            build.setdefault('downloadUrl', 'NoURL')
            build.setdefault('fileId', 0)
            build.setdefault('baseFileName', 'NoFileName')
            self.handle.ui.info('Build %d\t%s\t%d\t%s',
                buildId,
                build['baseFileName'],
                build['fileId'],
                build['downloadUrl'])
