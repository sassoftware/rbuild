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
platforms
'''
from rbuild import pluginapi
from rbuild.pluginapi import command


class ListPlatformsCommand(command.ListCommand):
    help = 'list platforms'
    resource = 'platforms'
    fieldMap = (('Label', lambda p: p.label),
                ('Enabled', lambda p: p.enabled),
                )


class Platforms(pluginapi.Plugin):
    name = 'platforms'

    def initialize(self):
        self.handle.Commands.getCommandClass('list').registerSubCommand(
            'platforms', ListPlatformsCommand)

    def list(self, *args, **kwargs):
        # default to not showing hidden platforms
        showHidden = kwargs.pop('hidden', False)
        platforms = self.handle.facade.rbuilder.getPlatforms(*args, **kwargs)
        if platforms:
            return [p for p in platforms
                    if p.hidden == 'false' or showHidden]
