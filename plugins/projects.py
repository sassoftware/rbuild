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


class DeleteProjectsCommand(command.BaseCommand):
    help = 'Delete project(s)'
    paramHelp = '<short name|label>+'

    def runCommand(self, handle, argSet, args):
        _, projects = self.requireParameters(
            args, expected=['PROJECT'], appendExtra=True)
        for project in projects:
            handle.Projects.delete(project)


class ListProjectsCommand(command.ListCommand):
    help = 'list projects'
    resource = 'projects'
    listFields = ('short_name', 'description', 'repository_hostname',)
    showFieldMap = dict(
        members=dict(hidden=True),
        images=dict(hidden=True),
        created_by=dict(
            accessor=lambda p: p.created_by.full_name if p.created_by else '',
            ),
        modified_by=dict(
            accessor=lambda p: p.modified_by.full_name if p.modified_by else '',
            ),
        project_branches=dict(
            accessor=lambda p: ', '.join(b.name for b in p.project_branches)
                if p.project_branches else '',
            ),
        project_branch_stages=dict(
            accessor=lambda p: ', '.join(s.name for s in p.project_branch_stages)
                if p.project_branch_stages else '',
            ),
        )


class Projects(pluginapi.Plugin):
    name = 'projects'
    prePrompt = 'This will delete the following branches and their stages:'
    prompt = 'This may lead to issues with other projects that refer to %s' + \
        ' branch%s.\nConfirm by typing DELETE'

    def delete(self, project):
        if '.' in project:
            # project is a label, get the shortname
            project = project.split('.')[0]
        project = self.handle.facade.rbuilder.getProject(project)
        self.handle.ui.write(self.prePrompt)
        for branch in project.project_branches:
            self.handle.ui.write('    %s' % branch.label)
        self.handle.ui.write()
        if project.project_branches == '1':
            args = ('this', '')
        else:
            args = ('these', 'es')
        response = self.handle.ui.getResponse(self.prompt % args)

        if response.upper() == 'DELETE':
            project.delete()

    def initialize(self):
        self.handle.Commands.getCommandClass('delete').registerSubCommand(
            self.name, DeleteProjectsCommand)
        self.handle.Commands.getCommandClass('list').registerSubCommand(
            self.name, ListProjectsCommand)

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

    def show(self, projectName):
        return self.handle.facade.rbuilder.getProject(projectName)
