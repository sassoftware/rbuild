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
"""
watch command and related utilities.
"""
from rbuild import pluginapi
from rbuild.pluginapi import command

class WatchCommand(command.CommandWithSubCommands):
    help = 'Watches details about the result of rbuild operations'

    commands = ['watch']

class WatchJobCommand(command.BaseCommand):
    # unused argument
    #pylint: disable-msg=W0613
    def runCommand(self, handle, argSet, args):
        jobId, = self.requireParameters(args, 'jobId')[1:]
        handle.Build.watchJob(jobId)

class WatchPackagesCommand(command.BaseCommand):
    def runCommand(self, handle, argSet, args):
        self.requireParameters(args)
        handle.Watch.watchPackages()

class WatchGroupsCommand(command.BaseCommand):
    def runCommand(self, handle, argSet, args):
        self.requireParameters(args)
        handle.Watch.watchGroups()


class Watch(pluginapi.Plugin):
    name = 'watch'

    def initialize(self):
        cmd = self.handle.Commands.getCommandClass('watch')
        cmd.registerSubCommand('groups', WatchGroupsCommand)
        cmd.registerSubCommand('packages', WatchPackagesCommand)
        cmd.registerSubCommand('job', WatchJobCommand)

    def registerCommands(self):
        self.handle.Commands.registerCommand(WatchCommand)

    def watchPackages(self):
        jobId = self.handle.getProductStore().getPackageJobId()
        self.handle.Build.watchJob(jobId)

    def watchGroups(self):
        jobId = self.handle.getProductStore().getGroupJobId()
        self.handle.Build.watchJob(jobId)
