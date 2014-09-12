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
from testutils import mock

from rbuild_test import rbuildhelp


class ProjectTest(rbuildhelp.RbuildHelper):
    def setUp(self):
        rbuildhelp.RbuildHelper.setUp(self)
        self.handle = self.getRbuildHandle()
        self.handle.Delete.registerCommands()
        self.handle.List.registerCommands()
        self.handle.Delete.initialize()
        self.handle.List.initialize()
        self.handle.Projects.initialize()

class DeleteProjectTest(ProjectTest):
    def setUp(self):
        ProjectTest.setUp(self)

        self.project1_branch1 = mock.MockObject()
        self.project1_branch1._mock.set( label='bar.example.com@sas:bar-1')

        self.project2_branch1 = mock.MockObject()
        self.project2_branch1._mock.set( label='foo.example.com@sas:foo-1')

        self.project2_branch2 = mock.MockObject()
        self.project2_branch2._mock.set( label='foo.example.com@sas:foo-2')

        self.project1 = mock.MockObject()
        self.project1._mock.set(
            project_branches=[self.project1_branch1], name='Bar Project')

        self.project2 = mock.MockObject()
        self.project2._mock.set(
            project_branches=[self.project2_branch1, self.project2_branch2],
            name='Foo Project')

    def testCommandParsing(self):
        handle = self.handle

        cmd = handle.Commands.getCommandClass('delete')()

        mock.mockMethod(handle.facade.rbuilder.getProject, self.project1)
        mock.mock(handle, 'ui')
        handle.ui.getResponse._mock.setDefaultReturn('no')

        # test no projects listed
        err = self.assertRaises(errors.ParseError, cmd.runCommand, handle, {},
            ['rbuild', 'delete', 'projects'])
        self.assertIn('PROJECT', str(err))

        # test non-DELETE response
        cmd.runCommand(handle, {}, ['rbuild', 'delete', 'projects', 'bar'])
        handle.facade.rbuilder.getProject._mock.assertCalled('bar')
        handle.ui.write._mock.assertCalled("This will delete the following"
            " branch and its stage(s):")
        handle.ui.write._mock.assertCalled("    bar.example.com@sas:bar-1")
        handle.ui.getResponse._mock.assertCalled("This may lead to issues with"
            " other projects that refer to this branch.\nConfirm by typing"
            " DELETE")
        handle.ui.write._mock.assertCalled(
            "Not deleting project 'Bar Project'")
        self.project1.delete._mock.assertNotCalled()

        # test delete
        handle.ui.getResponse._mock.setDefaultReturn('DELETE')
        cmd.runCommand(handle, {}, ['rbuild', 'delete', 'projects', 'bar'])
        handle.facade.rbuilder.getProject._mock.assertCalled('bar')
        handle.ui.write._mock.assertCalled("Deleting project 'Bar Project'")
        self.project1.delete._mock.assertCalled()

        # test label on comand line
        cmd.runCommand(handle, {}, ['rbuild', 'delete', 'projects',
            'bar.example.com@sas:bar-1'])
        handle.facade.rbuilder.getProject._mock.assertCalled('bar')
        handle.ui.write._mock.assertCalled("Deleting project 'Bar Project'")
        self.project1.delete._mock.assertCalled()

        # test project with more than one branch
        handle.facade.rbuilder.getProject._mock.setDefaultReturn(self.project2)
        cmd.runCommand(handle, {}, ['rbuild', 'delete', 'projects', 'foo'])
        handle.facade.rbuilder.getProject._mock.assertCalled('foo')
        handle.ui.write._mock.assertCalled("This will delete the following"
            " branches and their stage(s):")
        handle.ui.write._mock.assertCalled("    foo.example.com@sas:foo-1")
        handle.ui.write._mock.assertCalled("    foo.example.com@sas:foo-2")
        handle.ui.getResponse._mock.assertCalled("This may lead to issues with"
            " other projects that refer to these branches.\nConfirm by typing"
            " DELETE")
        handle.ui.write._mock.assertCalled("Deleting project 'Foo Project'")
        self.project2.delete._mock.assertCalled()


class ListProjectsTest(ProjectTest):
    def testCommandParsing(self):
        handle = self.handle

        cmd = handle.Commands.getCommandClass('list')()

        mock.mockMethod(handle.Projects.list)

        cmd.runCommand(handle, {}, ['rbuild', 'list', 'projects'])
        handle.Projects.list._mock.assertCalled()

    def testCommand(self):
        self.getRbuildHandle()
        self.checkRbuild(
            'list projects',
            'rbuild_plugins.projects.ListProjectsCommand.runCommand',
            [None, None, {}, ['list', 'projects']],
            )


class ProjectsPluginTest(rbuildhelp.RbuildHelper):
    def testList(self):
        handle = self.getRbuildHandle()

        mock.mockMethod(handle.facade.rbuilder.getProjects)

        _project1 = mock.MockObject()
        _project2 = mock.MockObject()
        _project3 = mock.MockObject()

        handle.facade.rbuilder.getProjects._mock.setReturn(
            [_project1], disabled='false', hidden='false')
        handle.facade.rbuilder.getProjects._mock.setReturn(
            [_project2], disabled='true', hidden='false')
        handle.facade.rbuilder.getProjects._mock.setReturn(
            [_project3], disabled='false', hidden='true')
        handle.facade.rbuilder.getProjects._mock.setReturn(
            [_project1, _project2], disabled='true', hidden='true')

        rv = handle.Projects.list()
        self.assertEqual(rv, [_project1])

        rv = handle.Projects.list(disabled='false')
        self.assertEqual(rv, [_project1])

        rv = handle.Projects.list(hidden='false')
        self.assertEqual(rv, [_project1])

        rv = handle.Projects.list(disabled='false', hidden='false')
        self.assertEqual(rv, [_project1])

        rv = handle.Projects.list(disabled='true')
        self.assertEqual(rv, [_project2])

        rv = handle.Projects.list(disabled='true', hidden='false')
        self.assertEqual(rv, [_project2])

        rv = handle.Projects.list(hidden='true')
        self.assertEqual(rv, [_project3])

        rv = handle.Projects.list(hidden='true', disabled='false')
        self.assertEqual(rv, [_project3])

        rv = handle.Projects.list(hidden='true', disabled='true')
        self.assertEqual(rv, [_project1, _project2])
