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
status command and related utilities.
"""
from rbuild import pluginapi
from rbuild.pluginapi import command

class ShowCommand(command.CommandWithSubCommands):
    help = 'Shows details about the result of rbuild operations'

    commands = ['show']

class Show(pluginapi.Plugin):
    name = 'show'

    def registerCommands(self):
        self.handle.Commands.registerCommand(ShowCommand)

    def showJobStatus(self, jobId):
        self.handle.facade.rmake.displayJob(jobId)
