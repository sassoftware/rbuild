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

import datetime

from rbuild import errors
from rbuild import pluginapi
from rbuild.pluginapi import command

class BuildReleaseCommand(command.BaseCommand):
    '''
    Builds release from most recent image job built on current stage.
    '''
    help = 'Build release from most recent image job for this stage'
    docs = {'release-name' :
                'name to assign to release (<stagename> images)',
            'release-version' :
                'version to assign to release (product version)',
            'release-description' :
                'description to assign to release (product description)',
           }


    def addLocalParameters(self, argDef):
        argDef['release-name'] = command.ONE_PARAM
        argDef['release-version'] = command.ONE_PARAM
        argDef['release-description'] = command.ONE_PARAM

    #pylint: disable-msg=R0201,R0903
    # could be a function, and too few public methods
    def runCommand(self, handle, argSet, args):
        name = argSet.pop('release-name', None)
        version = argSet.pop('release-version', None)
        description = argSet.pop('release-description', None)
        jobId = handle.productStore.getImageJobId()
        if not jobId:
            raise errors.PluginError('No image Job to build a release from')
        handle.Build.watchJob(jobId) # build may still be going
        if not handle.facade.rmake.isJobBuilt(jobId):
            raise errors.PluginError('Image build failed')
        handle.productStore.setStageReleaseId(None)
        releaseId = handle.BuildRelease.buildRelease(jobId,
            name=name, version=version, description=description)
        handle.productStore.setStageReleaseId(releaseId)
        # do not try to compose two releases from one image job
        handle.productStore.setImageJobId(None)


class BuildRelease(pluginapi.Plugin):
    name = 'buildrelease'

    def initialize(self):
        self.handle.Commands.getCommandClass('build').registerSubCommand(
                                    'release', BuildReleaseCommand)

    def buildRelease(self, jobId, name=None, version=None, description=None):
        """
        Create a release in rBuilder from the build ids referenced by the
        given job id.  Keyword arguments will be given default values.
        The default values chosen are not part of the API and may change
        from release to release.

        Prints (at info level) human-readable and script-readable output

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
        handle = self.handle
        buildIds = handle.facade.rmake.getBuildIdsFromJobId(jobId)
        releaseId = handle.facade.rbuilder.createRelease(buildIds)
        ui = handle.ui
        productStore = handle.productStore
        product = handle.product

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
                handle.getConfig().user[0],
                self._getTimeString())

        handle.facade.rbuilder.updateRelease(releaseId, name=name,
            version=version, description=description)
        # script-friendly output
        ui.info('Release %d\t%s\t%s',
            releaseId,
            name,
            handle.facade.rbuilder.getReleaseUrl(releaseId))
        # human-friendly output
        ui.info('Created release "%s", release id %s' %(name, releaseId))
        return releaseId

    @staticmethod
    def _getTimeString():
        return datetime.datetime.now().ctime()
