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
            'no-recurse' : 'default behavior left for backwards compatibility',
            'recurse' : 'build every package listed on the '
                'command line plus all of its dependencies',
      }



    def addLocalParameters(self, argDef):
        argDef['no-watch'] = command.NO_PARAM
        argDef['no-commit'] = command.NO_PARAM
        argDef['no-recurse'] = command.NO_PARAM
        argDef['recurse'] = command.NO_PARAM
        argDef['refresh'] = command.NO_PARAM
        argDef['message'] = '-m', command.ONE_PARAM

    #pylint: disable-msg=R0201,R0903
    # could be a function, and too few public methods
    def runCommand(self, handle, argSet, args):
        watch = not argSet.pop('no-watch', False)
        commit = not argSet.pop('no-commit', False)
        recurse = argSet.pop('recurse', False)
        argSet.pop('no-recurse', False)  # ignored, now the default
        refreshArg = argSet.pop('refresh', False)
        message = argSet.pop('message', None)
        success = True
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
            success = handle.Build.watchAndCommitJob(jobId, message)
        elif watch:
            success = handle.Build.watchJob(jobId)

        if not success:
            raise errors.PluginError('Package build failed')

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
