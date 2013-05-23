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

from rbuild_test import rbuildhelp
from testutils import mock


class CreateProjectBranchTest(rbuildhelp.RbuildHelper):

    def testCreateProjectArgParse(self):
        self.getRbuildHandle()
        self.checkRbuild('create project --name=title --short-name=short '
                '--domain-name=project.domain',
            'rbuild_plugins.createprojectbranch.CreateProjectCommand.runCommand',
            [None, None, {
                'name': 'title',
                'short-name': 'short',
                'domain-name': 'project.domain',
                }, ['create', 'project']])

    def testCreateProjectCmdline(self):
        handle = self.getRbuildHandle(mock.MockObject())
        handle.Create.registerCommands()
        handle.CreateProjectBranch.initialize()
        mock.mockMethod(handle.facade.rbuilder.createProject)
        cmd = handle.Commands.getCommandClass('create')()
        cmd.runCommand(handle, {
            'name': 'project name',
            'short-name': 'shortname',
            'domain-name': '',
            }, ['rbuild', 'create', 'project'])
        handle.facade.rbuilder.createProject._mock.assertCalled(
                title='project name', shortName='shortname', domainName='')

    def testCreateProjectInteractive(self):
        handle = self.getRbuildHandle(mock.MockObject())
        handle.Create.registerCommands()
        handle.CreateProjectBranch.registerCommands()
        mock.mockMethod(handle.facade.rbuilder.createProject)
        mock.mock(handle, 'ui')
        handle.ui.getResponse._mock.appendReturn(
                'project name', "Project name")
        handle.ui.getResponse._mock.appendReturn(
                'shortname', "Unique name",
                validationFn=handle.facade.rbuilder.isValidShortName)
        handle.ui.input._mock.appendReturn(
                'domain.name', "Domain name (blank for default): ")
        cmd = handle.Commands.getCommandClass('create')()
        cmd.runCommand(handle, {}, ['rbuild', 'create', 'project'])
        handle.facade.rbuilder.createProject._mock.assertCalled(
                title='project name', shortName='shortname',
                domainName='domain.name')
