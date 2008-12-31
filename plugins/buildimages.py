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

import datetime

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
        jobId = handle.BuildImages.buildImages(imageNames)
        if watch:
            handle.Build.watchJob(jobId)
            if handle.facade.rmake.isJobBuilt(jobId) and release:
                releaseId = handle.BuildImages.buildRelease(jobId,
                    name=name, version=version, description=description)
                handle.productStore.setStageReleaseId(releaseId)
        elif release:
            handle.ui.writeError('Not grouping built images into a release'
                                 ' due to --no-watch option.')


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

    def buildRelease(self, jobId, name=None, version=None, description=None):
        """
        Create a release in rBuilder from the build ids referenced by the
        given job id.  Keyword arguments will be given default values.
        The default values chosen are not part of the API and may change
        from release to release.

        @param jobId: Create a release from this job
        @type jobId: int
        @param name: Name of the release
        @type name: string
        @param version: Version of the release
        @type version: string
        @param description: Description of the release
        @type description: string
        """
        if not jobId:
            return None
        buildIds = self.handle.facade.rmake.getBuildIdsFromJobId(jobId)
        releaseId = self.handle.facade.rbuilder.createRelease(buildIds)
        ui = self.handle.ui
        productStore = self.handle.productStore
        product = self.handle.product

        # Update the created release with some relevant data.
        if name is None:
            stageName = productStore.getActiveStageName()
            name = '%s images' % stageName
        if version is None:
            version = product.getProductVersion()
        if description is None:
            description = product.getProductDescription()
        if not description:
            # empty productDescription, say something possibly useful
            description = 'Release built by %s on %s' % (
                self.handle.getConfig().user[0],
                self._getTimeString())

        self.handle.facade.rbuilder.updateRelease(releaseId, name=name,
            version=version, description=description)
        ui.write('Created release "%s", release id %s' %(name, releaseId))
        return releaseId

    @staticmethod
    def _getTimeString():
        return datetime.datetime.now().ctime()
