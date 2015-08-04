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
from collections import namedtuple

from rbuild import errors
from rbuild import pluginapi
from rbuild.pluginapi import command


ImageTypeProxy = namedtuple("ImageTypeProxy", ("name", "description"))


class ListImageTypesCommand(command.ListCommand):
    help = "List available image types"
    resource = "imagetypes"
    listFields = ("name", "description")


class ImageTypes(pluginapi.Plugin):
    name = 'imagetypes'

    def initialize(self):
        for command, subcommand, commandClass in (
                ('list', 'imagetypes', ListImageTypesCommand),
                ):
            cmd = self.handle.Commands.getCommandClass(command)
            cmd.registerSubCommand(subcommand, commandClass)

    def list(self, showAll=False):
        rb = self.handle.facade.rbuilder
        if self.handle.product is not None:
            # update the productdef so we have latest platform
            self.handle.productStore.update()
            availableTypes = set(
                bt.containerTemplateRef for bt in
                self.handle.product.getPlatformBuildTemplates())
        else:
            availableTypes = None
        types = (type for type in rb.getImageTypes() if type.name)
        if availableTypes:
            types = (type for type in types if type.name in availableTypes)
        return sorted(types, key=lambda t: (t.name, t.description))
