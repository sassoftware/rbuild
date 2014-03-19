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
        jobIds = self.handle.productStore.getImageJobIds()
        self.handle.facade.rbuilder.watchImages(jobIds)
