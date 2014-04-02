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
branches
'''
from rbuild import pluginapi
from rbuild.pluginapi import command


class ListBranchesCommand(command.ListCommand):
    help = 'list branches'
    resource = 'branches'
    listFields = ('name', 'label')

    def runCommand(self, handle, argSet, args):
        _, project = self.requireParameters(args, expected="PROJECT")
        self._list(handle, project)


class Branches(pluginapi.Plugin):
    name = 'branches'

    def initialize(self):
        self.handle.Commands.getCommandClass('list').registerSubCommand(
            'branches', ListBranchesCommand)

    def list(self, *args, **kwargs):
        '''
            List branches

            @param project: project to get branches from
            @type projecct: str or robj(project)
            @param order_by: field to order by, add '-' to indicate
            descending
            @param **kwargs: keyword args of field name and value to fitler
            on
        '''
        return self.handle.facade.rbuilder.getProjectBranches(*args, **kwargs)
