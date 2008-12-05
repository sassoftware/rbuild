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

class BuildImagesCommand(command.BaseCommand):
    '''
    Builds specified images for the current stage.  If no images are specified,
    builds all images defined by the product.
    '''
    help = 'Build images for this stage'
    paramHelp = '[image name]*'
    docs = {'no-watch' : 'do not watch the job after starting',
           }


    def addLocalParameters(self, argDef):
        argDef['no-watch'] = command.NO_PARAM

    #pylint: disable-msg=R0201,R0903
    # could be a function, and too few public methods
    def runCommand(self, handle, argSet, args):
        watch = not argSet.pop('no-watch', False)
        _, imageNames = self.requireParameters(args, allowExtra=True)
        if imageNames == []:
            imageNames = None
        jobId = handle.BuildImages.buildImages(imageNames)
        if watch:
            handle.Build.watchJob(jobId)


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
        '''
        self.handle.Build.warnIfOldProductDefinition('building images')
        job = self.handle.facade.rmake.createImagesJobForStage(names)
        jobId = self.handle.facade.rmake.buildJob(job)
        self.handle.productStore.setImageJobId(jobId)
        return jobId

