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
                                    'packages', BuildPackagesCommand,
                                    aliases=['package', ])

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
