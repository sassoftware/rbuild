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

from rbuild import errors
from collections import namedtuple
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
                title='project name',
                shortName='shortname',
                domainName='',
                description='',
                )

    def testCreateProjectInteractive(self):
        handle = self.getRbuildHandle(mock.MockObject())
        handle.Create.registerCommands()
        handle.CreateProjectBranch.registerCommands()
        handle.CreateProjectBranch.initialize()
        mock.mockMethod(handle.facade.rbuilder.createProject)
        mock.mock(handle, 'ui')
        handle.ui.getResponse._mock.appendReturn(
                'project name', "Project name")
        handle.ui.input._mock.appendReturn(
                'desc', "Project description (optional): ")
        handle.ui.getResponse._mock.appendReturn(
                'shortname', "Unique name",
                validationFn=handle.facade.rbuilder.isValidShortName)
        handle.ui.input._mock.appendReturn(
                'domain.name', "Domain name (blank for default): ")
        cmd = handle.Commands.getCommandClass('create')()
        cmd.runCommand(handle, {}, ['rbuild', 'create', 'project'])
        handle.facade.rbuilder.createProject._mock.assertCalled(
                title='project name',
                shortName='shortname',
                domainName='domain.name',
                description='desc',
                )

    def testCreateBranchArgParse(self):
        self.getRbuildHandle()
        self.checkRbuild('create branch --project=proj --branch=branch',
            'rbuild_plugins.createprojectbranch.CreateBranchCommand.runCommand',
            [None, None, {
                'project': 'proj',
                'branch': 'branch',
                }, ['create', 'branch']])

    def testCreateBranchCmdline(self):
        handle = self.getRbuildHandle(mock.MockObject())
        handle.Create.registerCommands()
        handle.CreateProjectBranch.initialize()
        mock.mockMethod(handle.facade.rbuilder.listPlatforms)
        mock.mockMethod(handle.facade.rbuilder.createBranch)
        mock.mock(handle, 'ui')
        Platform = namedtuple('Platform', 'platformName label id')
        handle.facade.rbuilder.listPlatforms._mock.setReturn([
            Platform('the platform', 'the@platform', 'http://the/platform'),
            Platform('not platform', 'not@platform', 'http://not/platform'),
            ])
        cmd = handle.Commands.getCommandClass('create')()
        cmd.runCommand(handle, {
            'project': 'proj',
            'branch': 'branch',
            'platform': 'the platform',
            }, ['rbuild', 'create', 'branch'])
        handle.facade.rbuilder.createBranch._mock.assertCalled(
                project='proj',
                name='branch',
                platformId='http://the/platform',
                namespace=None,
                description='',
                )
        err = self.assertRaises(errors.PluginError,
                cmd.runCommand, handle, {
                'project': 'proj',
                'branch': 'branch',
                'platform': 'missing platform',
                }, ['rbuild', 'create', 'branch'])
        self.assertEquals(str(err),
                "No platform matching term 'missing platform' was found")

    def testCreateBranchInteractive(self):
        handle = self.getRbuildHandle(mock.MockObject())
        handle.Create.registerCommands()
        handle.CreateProjectBranch.registerCommands()
        handle.CreateProjectBranch.initialize()
        mock.mockMethod(handle.facade.rbuilder.listPlatforms)
        mock.mockMethod(handle.facade.rbuilder.createBranch)
        mock.mock(handle, 'ui')
        Platform = namedtuple('Platform', 'platformName label id')
        rb = handle.facade.rbuilder
        rb.listPlatforms._mock.setReturn([
            Platform('the platform', 'the@platform', 'http://the/platform'),
            Platform('not platform', 'not@platform', 'http://not/platform'),
            ])
        handle.ui.getResponse._mock.appendReturn('proj', "Project name", validationFn=rb.isValidShortName)
        handle.ui.getResponse._mock.appendReturn('branch', "Branch name", validationFn=rb.isValidBranchName)
        handle.ui.input._mock.appendReturn('desc', "Branch description (optional): ")
        handle.ui.input._mock.appendReturn('nsp', "Namespace (blank for default): ")
        choiceArgs = ("Platform", [
            'the platform - the@platform',
            'not platform - not@platform'],
            "The following platforms are available:")
        handle.ui.getChoice._mock.setReturn(0, *choiceArgs)
        cmd = handle.Commands.getCommandClass('create')()
        cmd.runCommand(handle, {}, ['rbuild', 'create', 'branch'])
        rb.createBranch._mock.assertCalled(
                project='proj',
                name='branch',
                platformId='http://the/platform',
                namespace='nsp',
                description='desc',
                )
