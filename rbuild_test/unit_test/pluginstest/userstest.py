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


class AbstractUsersTest(rbuildhelp.RbuildHelper):
    def setUp(self):
        rbuildhelp.RbuildHelper.setUp(self)
        handle = self.getRbuildHandle()
        handle.Create.registerCommands()
        handle.Delete.registerCommands()
        handle.Edit.registerCommands()
        handle.List.registerCommands()
        handle.Users.registerCommands()
        handle.Create.initialize()
        handle.Delete.initialize()
        handle.Edit.initialize()
        handle.List.initialize()
        handle.Users.initialize()
        self.handle = handle


class CreateUserTest(AbstractUsersTest):
    def testCreateUserArgParse(self):
        self.checkRbuild(
            'create user --external --admin --create-resources'
            ' --password password username "full name" email@example.com',
            'rbuild_plugins.users.CreateUserCommand.runCommand',
            [None, None, {
                'external': True,
                'admin': True,
                'create-resources': True,
                'password': 'password',
                }, ['create', 'user', 'username', 'full name',
                    'email@example.com']])

        self.checkRbuild(
            'create user -e -a -c -p password username "full name"'
            ' email@example.com',
            'rbuild_plugins.users.CreateUserCommand.runCommand',
            [None, None, {
                'external': True,
                'admin': True,
                'create-resources': True,
                'password': 'password',
                }, ['create', 'user', 'username', 'full name',
                    'email@example.com']])

    def testCreateUserCmdline(self):
        handle = self.handle

        mock.mockMethod(handle.Users.create)
        mock.mockMethod(handle.ui.getPassword)

        cmd = handle.Commands.getCommandClass('create')()

        err = self.assertRaises(errors.ParseError,
            cmd.runCommand, handle, {}, ['rbuild', 'create', 'user'])
        self.assertEqual("'user' missing 3 command parameter(s): USERNAME,"
            " FULL_NAME, EMAIL", str(err))

        err = self.assertRaises(errors.ParseError,
            cmd.runCommand, handle, {}, ['rbuild', 'create', 'user', 'foo'])
        self.assertEqual("'user' missing 2 command parameter(s): FULL_NAME,"
            " EMAIL", str(err))

        err = self.assertRaises(errors.ParseError,
            cmd.runCommand, handle, {}, ['rbuild', 'create', 'user', 'foo',
            '"full name"'])
        self.assertEqual("'user' missing 1 command parameter(s): EMAIL",
            str(err))

        err = self.assertRaises(errors.BadParameterError,
            cmd.runCommand, handle, {'external': True, 'password': 'foo'},
            ['rbuild', 'create', 'user', 'foo', '"Foo Bar"', 'foo@example.com'])
        self.assertIn('external authentication', str(err))

        handle.ui.getPassword._mock.setReturn('secret', 'Password')
        cmd.runCommand(handle, {},
            ['rbuild', 'create', 'user', 'foo', 'Foo Bar', 'foo@example.com'])
        handle.Users.create._mock.assertCalled('foo', 'Foo Bar',
            'foo@example.com', 'secret', False, False, False)

        cmd.runCommand(handle, {'external': True},
            ['rbuild', 'create', 'user', 'foo', 'Foo Bar', 'foo@example.com'])
        handle.Users.create._mock.assertCalled('foo', 'Foo Bar',
            'foo@example.com', None, True, False, False)

        cmd.runCommand(handle, {'external': True, 'admin': True},
            ['rbuild', 'create', 'user', 'foo', 'Foo Bar', 'foo@example.com'])
        handle.Users.create._mock.assertCalled('foo', 'Foo Bar',
            'foo@example.com', None, True, True, False)

        cmd.runCommand(handle,
            {'external': True, 'admin': True, 'create-resources': True},
            ['rbuild', 'create', 'user', 'foo', 'Foo Bar', 'foo@example.com'])
        handle.Users.create._mock.assertCalled('foo', 'Foo Bar',
            'foo@example.com', None, True, True, True)


class ListUsersTest(AbstractUsersTest):
    def testCommand(self):
        self.getRbuildHandle()
        self.checkRbuild('list users',
            'rbuild_plugins.users.ListUsersCommand.runCommand',
            [None, None, {}, ['list', 'users']])
        self.checkRbuild('list users 1 2',
            'rbuild_plugins.users.ListUsersCommand.runCommand',
            [None, None, {}, ['list', 'users', '1', '2']])


class UsersTest(rbuildhelp.RbuildHelper):
    def testCreate(self):
        handle = self.getRbuildHandle()
        _client = mock.MockObject()
        mock.mockMethod(handle.facade.rbuilder._getRbuilderRESTClient, _client)

        err = self.assertRaises(errors.PluginError, handle.Users.create, 'foo',
            'foo bar', 'foo@example.com', 'secret', isExternal=True,
            isAdmin=True, createResources=True)
        self.assertIn('external authentication', str(err))

        err = self.assertRaises(errors.PluginError, handle.Users.create, 'foo',
            'foo bar', 'foo@example.com', '', isExternal=False,
            isAdmin=True, createResources=True)
        self.assertIn('Must provide', str(err))

        handle.Users.create('foo', 'foo bar', 'foo@example.com', 'secret',
            isExternal=False, isAdmin=False, createResources=False)
        doc = _client.api.users.append._mock.calls[0][0][0]
        self.assertEqual('foo', doc.user.user_name)
        self.assertEqual('foo bar', doc.user.full_name)
        self.assertEqual('foo@example.com', doc.user.email)
        self.assertEqual('secret', doc.user.password)
        self.assertFalse(doc.user.external_auth)
        self.assertFalse(doc.user.is_admin)
        self.assertFalse(doc.user.can_create)

        handle.Users.create('foo', 'foo bar', 'foo@example.com', None,
            isExternal=True, isAdmin=False, createResources=False)
        doc = _client.api.users.append._mock.calls[1][0][0]
        self.assertEqual('foo', doc.user.user_name)
        self.assertEqual('foo bar', doc.user.full_name)
        self.assertEqual('foo@example.com', doc.user.email)
        self.assertEqual(None, doc.user.password)
        self.assertTrue(doc.user.external_auth)
        self.assertFalse(doc.user.is_admin)
        self.assertFalse(doc.user.can_create)

        handle.Users.create('foo', 'foo bar', 'foo@example.com', None,
            isExternal=True, isAdmin=True, createResources=False)
        doc = _client.api.users.append._mock.calls[2][0][0]
        self.assertEqual('foo', doc.user.user_name)
        self.assertEqual('foo bar', doc.user.full_name)
        self.assertEqual('foo@example.com', doc.user.email)
        self.assertEqual(None, doc.user.password)
        self.assertTrue(doc.user.external_auth)
        self.assertTrue(doc.user.is_admin)
        self.assertFalse(doc.user.can_create)

        handle.Users.create('foo', 'foo bar', 'foo@example.com', None,
            isExternal=True, isAdmin=True, createResources=True)
        doc = _client.api.users.append._mock.calls[3][0][0]
        self.assertEqual('foo', doc.user.user_name)
        self.assertEqual('foo bar', doc.user.full_name)
        self.assertEqual('foo@example.com', doc.user.email)
        self.assertEqual(None, doc.user.password)
        self.assertTrue(doc.user.external_auth)
        self.assertTrue(doc.user.is_admin)
        self.assertTrue(doc.user.can_create)
