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
                '--domain-name=project.domain --description=description',
            'rbuild_plugins.createprojectbranch.CreateProjectCommand.runCommand',
            [None, None, {
                'name': 'title',
                'short-name': 'short',
                'domain-name': 'project.domain',
                'description': 'description',
            }, ['create', 'project']])

        self.checkRbuild('create project --name=title --short-name=short '
                '--domain-name=project.domain --description=description '
                '--external --upstream-url other.domain --auth-type auth '
                '--username user --password secret --entitlement entitle',
            'rbuild_plugins.createprojectbranch.CreateProjectCommand.runCommand',
            [None, None, {
                'name': 'title',
                'short-name': 'short',
                'domain-name': 'project.domain',
                'description': 'description',
                'external': True,
                'upstream-url': 'other.domain',
                'auth-type': 'auth',
                'username': 'user',
                'password': 'secret',
                'entitlement': 'entitle',
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

    def testCreateExternalProjectCmdline(self):
        handle = self.getRbuildHandle(mock.MockObject())
        handle.Create.registerCommands()
        handle.CreateProjectBranch.initialize()
        mock.mockMethod(handle.facade.rbuilder.createProject)
        cmd = handle.Commands.getCommandClass('create')()

        # no auth
        cmd.runCommand(handle, {
            'name': 'project name',
            'short-name': 'shortname',
            'domain-name': '',
            'external': True,
            'label': 'repo@n:branch',
            'upstream-url': 'http://foo.com',
            'auth-type': 'none',
            }, ['rbuild', 'create', 'project'])
        handle.facade.rbuilder.createProject._mock.assertCalled(
                title='project name',
                shortName='shortname',
                domainName='',
                description='',
                external=True,
                external_params=(
                    ['repo@n:branch'], 'http://foo.com', 'none', None,
                    None, None),
                )

        # userpass auth
        cmd.runCommand(handle, {
            'name': 'project name',
            'short-name': 'shortname',
            'domain-name': '',
            'external': True,
            'label': 'repo@n:branch',
            'upstream-url': 'http://foo.com',
            'auth-type': 'userpass',
            'username': 'user',
            'password': 'secret',
            }, ['rbuild', 'create', 'project'])
        handle.facade.rbuilder.createProject._mock.assertCalled(
                title='project name',
                shortName='shortname',
                domainName='',
                description='',
                external=True,
                external_params=(
                    ['repo@n:branch'], 'http://foo.com', 'userpass', 'user',
                    'secret', None),
                )

        # entitlement auth
        cmd.runCommand(handle, {
            'name': 'project name',
            'short-name': 'shortname',
            'domain-name': '',
            'external': True,
            'label': 'repo@n:branch',
            'upstream-url': 'http://foo.com',
            'auth-type': 'entitlement',
            'entitlement': 'entitle',
            }, ['rbuild', 'create', 'project'])
        handle.facade.rbuilder.createProject._mock.assertCalled(
                title='project name',
                shortName='shortname',
                domainName='',
                description='',
                external=True,
                external_params=(
                    ['repo@n:branch'], 'http://foo.com', 'entitlement', None,
                    None, 'entitle'),
                )

    def testCreateProjectInteractive(self):
        handle = self.getRbuildHandle(mock.MockObject())
        handle.Create.registerCommands()
        handle.CreateProjectBranch.registerCommands()
        handle.CreateProjectBranch.initialize()
        mock.mockMethod(handle.facade.rbuilder.createProject)
        mock.mock(handle, 'ui')
        handle.ui.getResponse._mock.appendReturn(
                'project name', "Project name (required)", required=True)
        handle.ui.getResponse._mock.appendReturn(
                'desc', "Project description (optional)")
        handle.ui.getResponse._mock.appendReturn(
                'shortname', "Unique name (required)",
                validationFn=handle.facade.rbuilder.isValidShortName,
                required=True)
        handle.ui.getResponse._mock.appendReturn(
                'domain.name', "Domain name (blank for default)",
                validationFn=handle.facade.rbuilder.isValidDomainName)
        cmd = handle.Commands.getCommandClass('create')()
        cmd.runCommand(handle, {}, ['rbuild', 'create', 'project'])
        handle.facade.rbuilder.createProject._mock.assertCalled(
                title='project name',
                shortName='shortname',
                domainName='domain.name',
                description='desc',
                )

    def testCreateExternalProjectInteractive(self):
        handle = self.getRbuildHandle(mock.MockObject())
        handle.Create.registerCommands()
        handle.CreateProjectBranch.registerCommands()
        handle.CreateProjectBranch.initialize()
        mock.mockMethod(handle.facade.rbuilder.createProject)
        mock.mock(handle.facade.rbuilder, 'isValidUrl')
        mock.mock(handle, 'ui')

        handle.facade.rbuilder.isValidUrl._mock.setReturn(True, "http://foo.com")
        handle.ui.getResponse._mock.appendReturn(
                'project name', "Project name (required)", required=True)
        handle.ui.getResponse._mock.appendReturn(
                'desc', "Project description (optional)")
        handle.ui.getResponse._mock.appendReturn(
                'shortname', "Unique name (required)",
                validationFn=handle.facade.rbuilder.isValidShortName,
                required=True)
        handle.ui.getResponse._mock.appendReturn(
                'domain.name', "Domain name (blank for default)",
                validationFn=handle.facade.rbuilder.isValidDomainName)
        handle.ui.getResponse._mock.appendReturn(
                'repo@n:branch', 'Upstream label (required)', required=True,
                validationFn=handle.facade.conary.isValidLabel)
        handle.ui.getResponse._mock.appendReturn(
                'http://foo.com', "URL of upstream repository (optional)")
        handle.ui.getResponse._mock.appendReturn(
                'user', "External username", required=True)
        handle.ui.getPassword._mock.appendReturn(
                'secret', "External password", verify=True)
        handle.ui.getResponse._mock.appendReturn(
                'entitle', 'External entitlement', required=True)

        cmd = handle.Commands.getCommandClass('create')()

        # auth-type none
        handle.ui.getChoice._mock.setReturn(
                0, "External authentication type",
                ['None', 'Username and Password', 'Entitlement key'], default=0)

        cmd.runCommand(handle, {'external': True},
                ['rbuild', 'create', 'project'])
        handle.facade.rbuilder.createProject._mock.assertCalled(
                title='project name',
                shortName='shortname',
                domainName='domain.name',
                description='desc',
                external=True,
                external_params=(
                    ['repo@n:branch'], 'http://foo.com', 'none', None, None,
                    None),
                )

        # auth-type userpass
        handle.ui.getChoice._mock.setReturn(
                1, "External authentication type",
                ['None', 'Username and Password', 'Entitlement key'], default=0)

        cmd.runCommand(handle, {'external': True},
                ['rbuild', 'create', 'project'])
        handle.facade.rbuilder.createProject._mock.assertCalled(
                title='project name',
                shortName='shortname',
                domainName='domain.name',
                description='desc',
                external=True,
                external_params=(
                    ['repo@n:branch'], 'http://foo.com', 'userpass', 'user',
                    'secret', None),
                )

        # auth-type entitlement
        handle.ui.getChoice._mock.setReturn(
                2, "External authentication type",
                ['None', 'Username and Password', 'Entitlement key'], default=0)

        cmd.runCommand(handle, {'external': True},
                ['rbuild', 'create', 'project'])
        handle.facade.rbuilder.createProject._mock.assertCalled(
                title='project name',
                shortName='shortname',
                domainName='domain.name',
                description='desc',
                external=True,
                external_params=(
                    ['repo@n:branch'], 'http://foo.com', 'entitlement', None,
                    None, 'entitle'),
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
                platformLabel='the@platform',
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
        handle.ui.getResponse._mock.appendReturn('proj',
            "Project name (required)", validationFn=rb.isValidShortName,
            required=True)
        handle.ui.getResponse._mock.appendReturn('branch',
            "Branch name (required)", validationFn=rb.isValidBranchName,
            required=True)
        handle.ui.getResponse._mock.appendReturn('desc',
            "Branch description (optional)")
        handle.ui.getResponse._mock.appendReturn('nsp',
            "Namespace (blank for default)")
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
                platformLabel='the@platform',
                namespace='nsp',
                description='desc',
                )
