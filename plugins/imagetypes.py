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
List image types
"""

from rbuild import pluginapi
from rbuild.pluginapi import command


class ListImageTypesCommand(command.ListCommand):
    help = "List image types"
    resource = "imagetypes"
    listFields = ("description", "name")


class ImageTypes(pluginapi.Plugin):
    name = 'imagetypes'

    def initialize(self):
        for command, subcommand, commandClass in (
                ('list', 'imagetypes', ListImageTypesCommand),
                ):
            cmd = self.handle.Commands.getCommandClass(command)
            cmd.registerSubCommand(subcommand, commandClass)

    def list(self):
        rb = self.handle.facade.rbuilder
        return [type for type in rb.getImageTypes() if type.name]
