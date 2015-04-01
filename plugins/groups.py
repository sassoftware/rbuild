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


'''
projects
'''
from rbuild import pluginapi
from rbuild.lib import util
from rbuild.productstore.decorators import requiresStage
from rbuild.pluginapi import command


class ListGroupsCommand(command.ListCommand):
    help = 'List groups'
    resource = 'groups'
    listFields = ('name', 'trailingVersion', 'imageCount', 'timeStamp')
    listFieldMap = {
        'trailingVersion': dict(display_name="Trailing Version"),
        'imageCount': dict(display_name="Image Count"),
        'timeStamp': dict(display_name="Created",
                          accessor=lambda g: util.convertTime(g.timeStamp))
        }


class Groups(pluginapi.Plugin):
    name = 'groups'

    def initialize(self):
        self.handle.Commands.getCommandClass('list').registerSubCommand(
            'groups', ListGroupsCommand)

    @requiresStage
    def list(self, *args, **kwargs):
        return sorted(
            self.handle.facade.rbuilder.getGroups(
                shortName=self.handle.product.getProductShortname(),
                label=self.handle.productStore.getActiveStageLabel(),
                **kwargs),
            key=lambda g: g.timeStamp, reverse=True)
