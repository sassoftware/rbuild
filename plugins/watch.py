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


"""
watch command and related utilities.
"""
from rbuild import pluginapi
from rbuild.pluginapi import command

class WatchCommand(command.CommandWithSubCommands):
    #pylint: disable-msg=R0923
    # "the creature can't help its ancestry"
    help = 'Watches details about the result of rbuild operations'

    commands = ['watch']

class WatchJobCommand(command.BaseCommand):
    def runCommand(self, handle, _, args):
        jobId, = self.requireParameters(args, 'jobId')[1:]
        handle.Build.watchJob(jobId)

class WatchPackagesCommand(command.BaseCommand):
    def runCommand(self, handle, _, args):
        self.requireParameters(args)
        handle.Watch.watchPackages()

class WatchGroupsCommand(command.BaseCommand):
    def runCommand(self, handle, _, args):
        self.requireParameters(args)
        handle.Watch.watchGroups()

class WatchImagesCommand(command.BaseCommand):
    def runCommand(self, handle, _, args):
        self.requireParameters(args)
        handle.Watch.watchImages()



class Watch(pluginapi.Plugin):
    name = 'watch'

    def initialize(self):
        cmd = self.handle.Commands.getCommandClass('watch')
        cmd.registerSubCommand('groups', WatchGroupsCommand)
        cmd.registerSubCommand('packages', WatchPackagesCommand)
        cmd.registerSubCommand('images', WatchImagesCommand)
        cmd.registerSubCommand('job', WatchJobCommand)

    def registerCommands(self):
        self.handle.Commands.registerCommand(WatchCommand)

    def watchPackages(self):
        jobId = self.handle.productStore.getPackageJobId()
        self.handle.Build.watchJob(jobId)

    def watchGroups(self):
        jobId = self.handle.productStore.getGroupJobId()
        self.handle.Build.watchJob(jobId)

    def watchImages(self):
        jobId = self.handle.productStore.getImageJobId()
        self.handle.Build.watchJob(jobId)
