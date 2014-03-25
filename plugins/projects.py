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
from rbuild.pluginapi import command


class ListProjectsCommand(command.ListCommand):
    help = 'list projects'
    fieldMap = (('Hostname', lambda p: p.repository_hostname),
                )
    resource = 'projects'


class Projects(pluginapi.Plugin):
    name = 'projects'

    def initialize(self):
        self.handle.Commands.getCommandClass('list').registerSubCommand(
            'projects', ListProjectsCommand)

    def list(self, *args, **kwargs):
        '''
            List projects

            @param order_by: field to order by, add '-' to indicate
            descending
            @param **kwargs: keyword args of field name and value to fitler
            on
        '''
        # default to not showing hidden or disabled projects
        hidden = kwargs.pop('hidden', 'false')
        disabled = kwargs.pop('disabled', 'false')

        return self.handle.facade.rbuilder.getProjects(
            disabled=disabled, hidden=hidden, **kwargs)
