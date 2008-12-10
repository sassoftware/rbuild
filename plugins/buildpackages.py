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

from rbuild_plugins.build import packages
from rbuild_plugins.build import refresh

class BuildPackagesCommand(command.BaseCommand):
    """
    Builds or rebuilds specified packages, or all checked-out packages
    if none are specified.

    Additionally, rebuilds any other packages in the product group that
    depend on the built packages.
    """

    help = 'Build edited packages for this stage'
    paramHelp = '[package]*'
    docs = {'refresh' : 'refreshes the source of specified packages, or all '
                'checked-out packages if none are specified',
            'message' : 'message describing why the commit was performed',
            'no-watch' : 'do not watch the job after starting the build',
            'no-commit' : 'do not automatically commit successful builds',
            'no-recurse' : 'build exactly the packages listed on the '
                'command line',
      }



    def addLocalParameters(self, argDef):
        argDef['no-watch'] = command.NO_PARAM
        argDef['no-commit'] = command.NO_PARAM
        argDef['no-recurse'] = command.NO_PARAM
        argDef['refresh'] = command.NO_PARAM
        argDef['message'] = '-m', command.ONE_PARAM

    #pylint: disable-msg=R0201,R0903
    # could be a function, and too few public methods
    def runCommand(self, handle, argSet, args):
        watch = not argSet.pop('no-watch', False)
        commit = not argSet.pop('no-commit', False)
        recurse = not argSet.pop('no-recurse', False)
        refreshArg = argSet.pop('refresh', False)
        _, packageList, = self.requireParameters(args, allowExtra=True)
        if not packageList:
            if refreshArg:
                handle.BuildPackages.refreshAllPackages()
            jobId = handle.BuildPackages.buildAllPackages()
        else:
            if refreshArg:
                handle.BuildPackages.refreshPackages(packageList)
            jobId = handle.BuildPackages.buildPackages(packageList, recurse)
        if watch and commit:
            handle.Build.watchAndCommitJob(jobId)
        elif watch:
            handle.Build.watchJob(jobId)


class BuildPackages(pluginapi.Plugin):

    def initialize(self):
        self.handle.Commands.getCommandClass('build').registerSubCommand(
                                    'packages', BuildPackagesCommand)

    def buildAllPackages(self):
        self.handle.Build.warnIfOldProductDefinition('building all packages')
        job = self.createJobForAllPackages()
        jobId = self.handle.facade.rmake.buildJob(job)
        self.handle.productStore.setPackageJobId(jobId)
        return jobId

    def buildPackages(self, packageList, recurse=True):
        self.handle.Build.warnIfOldProductDefinition('building packages')
        job = self.createJobForPackages(packageList, recurse)
        jobId = self.handle.facade.rmake.buildJob(job)
        self.handle.productStore.setPackageJobId(jobId)
        return jobId

    def createJobForAllPackages(self):
        return packages.createRmakeJobForAllPackages(self.handle)

    def createJobForPackages(self, packageList, recurse=True):
        return packages.createRmakeJobForPackages(self.handle, packageList,
            recurse)

    def refreshPackages(self, packageList=None):
        return refresh.refreshPackages(self.handle, packageList)

    def refreshAllPackages(self):
        return refresh.refreshAllPackages(self.handle)
