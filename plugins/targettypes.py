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
List target types
"""

from rbuild import pluginapi
from rbuild.pluginapi import command


class ListTargetTypesCommand(command.ListCommand):
    help = "List target types"
    resource = "targettypes"
    listFields = ("name", "description")


class TargetTypes(pluginapi.Plugin):
    name = 'targettypes'

    def initialize(self):
        for command, subcommand, commandClass in (
                ('list', 'targettypes', ListTargetTypesCommand),
                ):
            cmd = self.handle.Commands.getCommandClass(command)
            cmd.registerSubCommand(subcommand, commandClass)

    def list(self):
        return self.handle.facade.rbuilder.getTargetTypes()
