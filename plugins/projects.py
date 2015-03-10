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

    prePrompt = 'This will delete the following branch%s and %s stage(s):'
    prompt = ('This will permenantly destroy any content in this repository.'
              ' Confirm by typing DELETE')

    def runCommand(self, handle, argSet, args):
        _, projects = self.requireParameters(args, expected=['PROJECT'],
            appendExtra=True)

        for project in projects:
            if '.' in project:
                # project is a label, get the shortname
                project = project.split('.')[0]
            project = handle.facade.rbuilder.getProject(project)
            if project.project_branches:
                branch_count = len(project.project_branches)
            else:
                branch_count = 0

            if branch_count > 0:
                handle.ui.write(self.prePrompt %
                    (('es', 'their') if branch_count > 1 else ('', "its")))
                for branch in project.project_branches:
                    handle.ui.write('    %s' % branch.label)
                handle.ui.write()
                handle.ui.write('This may lead to issues with other projects '
                    'that refer to %s branch%s.\n' % (
                    ('these', 'es') if branch_count > 1 else ('this', '')))

            response = handle.ui.getResponse(self.prompt)
            if response.upper() == 'DELETE':
                handle.ui.write("Deleting project '%s'" % project.name)
                project.delete()
            else:
                handle.ui.write("Not deleting project '%s'" % project.name)


class ListProjectsCommand(command.ListCommand):
    help = 'list projects'
    resource = 'projects'
    listFields = ('short_name', 'description', 'repository_hostname',)
    showFieldMap = dict(
        members=dict(hidden=True),
        images=dict(hidden=True),
        password=dict(hidden=True),
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
