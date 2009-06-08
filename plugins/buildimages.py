#
# Copyright (c) 2008-2009 rPath, Inc.
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
        release = not argSet.pop('no-release', False)
        name = argSet.pop('release-name', None)
        version = argSet.pop('release-version', None)
        description = argSet.pop('release-description', None)
        _, imageNames = self.requireParameters(args, allowExtra=True)
        if imageNames == []:
            imageNames = None
        if release:
            # reset any previous definition of the current complete releaseId
            handle.productStore.setStageReleaseId(None)
        jobId = handle.BuildImages.buildImages(imageNames)
        if watch:
            handle.Build.watchJob(jobId)
            if not handle.facade.rmake.isJobBuilt(jobId):
                raise errors.PluginError('Image build failed')
            handle.BuildImages.printImageUrlsForJob(jobId)
            if release:
                releaseId = handle.BuildRelease.buildRelease(jobId,
                    name=name, version=version, description=description)
                handle.productStore.setStageReleaseId(releaseId)
                # do not try to compose two releases from one image job
                handle.productStore.setImageJobId(None)
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
