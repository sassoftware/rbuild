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

class BuildImagesCommand(command.BaseCommand):
    '''
    Builds specified images for the current stage.  If no images are specified,
    builds all images defined by the product.  

    Creates a release containing the built images.  The job must be watched
    for a release to be created.
    '''
    help = 'Build images for this stage'
    paramHelp = '[image name]*'
    docs = {'no-watch' : 'do not watch the job and do not create a'
                         ' release after starting',
            'no-release' : 'do not create a release',
            'release-name' :
                'name to assign to release (<stagename> images)',
            'release-version' :
                'version to assign to release (product version)',
            'release-description' :
                'description to assign to release (product description)',
           }


    def addLocalParameters(self, argDef):
        argDef['no-watch'] = command.NO_PARAM
        argDef['no-release'] = command.NO_PARAM
        argDef['release-name'] = command.ONE_PARAM
        argDef['release-version'] = command.ONE_PARAM
        argDef['release-description'] = command.ONE_PARAM

    #pylint: disable-msg=R0201,R0903
    # could be a function, and too few public methods
    def runCommand(self, handle, argSet, args):
        watch = not argSet.pop('no-watch', False)
        release = not argSet.pop('no-release', True)
        name = argSet.pop('release-name', None)
        version = argSet.pop('release-version', None)
        description = argSet.pop('release-description', None)
        _, imageNames = self.requireParameters(args, allowExtra=True)
        if imageNames == []:
            imageNames = None
        if release:
            # reset any previous definition of the current complete releaseId
            handle.productStore.setStageReleaseId(0)
        jobId = handle.BuildImages.buildImages(imageNames)
        if watch:
            handle.Build.watchJob(jobId)
            if not handle.facade.rmake.isJobBuilt(jobId):
                raise errors.PluginError('Image build failed')
            handle.BuildImages.printImageUrlsForJob(jobId)
            if release:
                releaseId = handle.BuildRelease.buildRelease(jobId,
                    name=name, version=version, description=description)
                # do not try to compose two releases from one image job
                handle.productStore.setImageJobId(0)
        elif release:
            handle.ui.writeError('Not grouping built images into a release'
                ' due to --no-watch option; use "rbuild build release" later.')


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
        job = self.handle.facade.rmake.createImagesJobForStage(names)
        jobId = self.handle.facade.rmake.buildJob(job)
        self.handle.productStore.setImageJobId(jobId)
        return jobId

    def printImageUrlsForJob(self, jobId):
        '''
        Print image URLs for all builds associated with an image job
        '''
        buildIds = self.handle.facade.rmake.getBuildIdsFromJobId(jobId)
        for buildId in buildIds:
            self.printImageUrlsForBuild(buildId)

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
