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

from rbuild_plugins.build import groups

class BuildGroupsCommand(command.BaseCommand):
    help = 'Build groups for this stage'
    docs = {'message' : 'message describing why the commit was performed',
            'no-watch' : 'do not watch the job after starting the build',
            'no-commit' : 'do not automatically commit successful builds',}

    def addLocalParameters(self, argDef):
        argDef['message'] = '-m', command.ONE_PARAM
        argDef['no-watch'] = command.NO_PARAM
        argDef['no-commit'] = command.NO_PARAM

    #pylint: disable-msg=R0201,R0903
    # could be a function, and too few public methods
    def runCommand(self, handle, argSet, args):
        watch = not argSet.pop('no-watch', False)
        commit = not argSet.pop('no-commit', False)
        message = argSet.pop('message', None)
        success = True
        _, groupList, = self.requireParameters(args, allowExtra=True)
        if not groupList:
            jobId = handle.BuildGroups.buildAllGroups()
        else:
            jobId = handle.BuildGroups.buildGroups(groupList)
        if watch and commit:
            success = handle.Build.watchAndCommitJob(jobId, message)
        elif watch:
            success = handle.Build.watchJob(jobId)

        if not success:
            raise errors.PluginError('Group build failed')


class BuildGroups(pluginapi.Plugin):

    def initialize(self):
        self.handle.Commands.getCommandClass('build').registerSubCommand(
                                    'groups', BuildGroupsCommand)

    def buildAllGroups(self):
        self.handle.Build.warnIfOldProductDefinition('building all groups')
        job = self.createJobForAllGroups()
        jobId = self.handle.facade.rmake.buildJob(job)
        self.handle.productStore.setGroupJobId(jobId)
        return jobId

    def buildGroups(self, groupList):
        self.handle.Build.warnIfOldProductDefinition('building groups')
        job = self.createJobForGroups(groupList)
        jobId = self.handle.facade.rmake.buildJob(job)
        self.handle.productStore.setGroupJobId(jobId)
        return jobId

    def createJobForAllGroups(self):
        return groups.createRmakeJobForAllGroups(self.handle)

    def createJobForGroups(self, groupList):
        return groups.createRmakeJobForGroups(self.handle, groupList)
