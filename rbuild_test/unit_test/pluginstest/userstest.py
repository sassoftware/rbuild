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
        handle.Users.initialize()
        self.handle = handle


class CreateUserTest(AbstractUsersTest):
    def testCreateUserArgParse(self):
        self.checkRbuild(
            'create user --external --admin --create-resources'
            ' --password password --user-name username --full-name "full name"'
            ' --email email@example.com',
            'rbuild_plugins.users.CreateUserCommand.runCommand',
            [None, None, {
                'external': True,
                'admin': True,
                'create-resources': True,
                'password': 'password',
                'full-name': 'full name',
                'email': 'email@example.com',
                'user-name': 'username',
                }, ['create', 'user']])

    def testCreateUserCmdline(self):
        handle = self.handle

        mock.mockMethod(handle.Users.create)
        mock.mockMethod(handle.ui.getPassword)
        mock.mockMethod(handle.ui.getResponse)

        cmd = handle.Commands.getCommandClass('create')()

        handle.ui.getResponse._mock.setReturn('foo', 'User name')
        handle.ui.getResponse._mock.setReturn('foo bar', 'Full name')
        handle.ui.getResponse._mock.setReturn('foo@example.com', 'Email')
        handle.ui.getPassword._mock.setReturn('secret', 'Password')

        cmd.runCommand(handle, {}, ['rbuild', 'create', 'user'])
        handle.Users.create._mock.assertCalled(user_name='foo',
            full_name='foo bar', email='foo@example.com', password='secret')

        cmd.runCommand(handle, {'user-name': 'bar'},
            ['rbuild', 'create', 'user'])
        handle.Users.create._mock.assertCalled(user_name='bar',
            full_name='foo bar', email='foo@example.com', password='secret')

        cmd.runCommand(handle, {'full-name': 'Full Name'},
            ['rbuild', 'create', 'user'])
        handle.Users.create._mock.assertCalled(user_name='foo',
            full_name='Full Name', email='foo@example.com', password='secret')

        cmd.runCommand(handle, {'email': 'email'},
            ['rbuild', 'create', 'user'])
        handle.Users.create._mock.assertCalled(user_name='foo',
            full_name='foo bar', email='email', password='secret')

        cmd.runCommand(handle, {'password': 'password'},
            ['rbuild', 'create', 'user'])
        handle.Users.create._mock.assertCalled(user_name='foo',
            full_name='foo bar', email='foo@example.com', password='password')

        cmd.runCommand(handle, {'external': True},
            ['rbuild', 'create', 'user'])
        handle.Users.create._mock.assertCalled(user_name='foo',
            full_name='foo bar', email='foo@example.com', external_auth=True)

        cmd.runCommand(handle, {'admin': True}, ['rbuild', 'create', 'user'])
        handle.Users.create._mock.assertCalled(user_name='foo',
            full_name='foo bar', email='foo@example.com', password='secret',
            is_admin=True)

        cmd.runCommand(handle, {'create-resources': True},
            ['rbuild', 'create', 'user'])
        handle.Users.create._mock.assertCalled(user_name='foo',
            full_name='foo bar', email='foo@example.com', password='secret',
            can_create=True)


class DeleteUsersTest(AbstractUsersTest):
    def testDeleteUserArgParse(self):
        self.checkRbuild('delete users foo',
            'rbuild_plugins.users.DeleteUsersCommand.runCommand',
            [None, None, {}, ['delete', 'users', 'foo']])

    def testDeleteUserCmdline(self):
        handle = self.handle

        mock.mockMethod(handle.Users.delete)
        mock.mockMethod(handle.ui.getYn)

        handle.ui.getYn._mock.setReturn(False, "Really delete user 'foo'",
            False)
        handle.ui.getYn._mock.setReturn(True, "Really delete user 'bar'",
            False)

        cmd = handle.Commands.getCommandClass('delete')()

        cmd.runCommand(handle, {}, ['rbuild', 'delete', 'users', 'foo'])
        handle.Users.delete._mock.assertNotCalled()

        cmd.runCommand(handle, {}, ['rbuild', 'delete', 'users', 'foo', 'bar'])
        handle.Users.delete._mock.assertCalled('bar')


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
            'foo bar', 'foo@example.com', 'secret', external_auth=True,
            is_admin=True, can_create=True)
        self.assertIn('external authentication', str(err))

        err = self.assertRaises(errors.PluginError, handle.Users.create, 'foo',
            'foo bar', 'foo@example.com', '', external_auth=False,
            is_admin=True, can_create=True)
        self.assertIn('Must provide', str(err))

        handle.Users.create('foo', 'foo bar', 'foo@example.com', 'secret',
            external_auth=False, is_admin=False, can_create=False)
        doc = _client.api.users.append._mock.calls[0][0][0]
        self.assertEqual('foo', doc.user.user_name)
        self.assertEqual('foo bar', doc.user.full_name)
        self.assertEqual('foo@example.com', doc.user.email)
        self.assertEqual('secret', doc.user.password)
        self.assertFalse(doc.user.external_auth)
        self.assertFalse(doc.user.is_admin)
        self.assertFalse(doc.user.can_create)

        handle.Users.create('foo', 'foo bar', 'foo@example.com', None,
            external_auth=True, is_admin=False, can_create=False)
        doc = _client.api.users.append._mock.calls[1][0][0]
        self.assertEqual('foo', doc.user.user_name)
        self.assertEqual('foo bar', doc.user.full_name)
        self.assertEqual('foo@example.com', doc.user.email)
        self.assertFalse(hasattr(doc.user, 'password'))
        self.assertTrue(doc.user.external_auth)
        self.assertFalse(doc.user.is_admin)
        self.assertFalse(doc.user.can_create)

        handle.Users.create('foo', 'foo bar', 'foo@example.com', None,
            external_auth=True, is_admin=True, can_create=False)
        doc = _client.api.users.append._mock.calls[2][0][0]
        self.assertEqual('foo', doc.user.user_name)
        self.assertEqual('foo bar', doc.user.full_name)
        self.assertEqual('foo@example.com', doc.user.email)
        self.assertFalse(hasattr(doc.user, 'password'))
        self.assertTrue(doc.user.external_auth)
        self.assertTrue(doc.user.is_admin)
        self.assertFalse(doc.user.can_create)

        handle.Users.create('foo', 'foo bar', 'foo@example.com', None,
            external_auth=True, is_admin=True, can_create=True)
        doc = _client.api.users.append._mock.calls[3][0][0]
        self.assertEqual('foo', doc.user.user_name)
        self.assertEqual('foo bar', doc.user.full_name)
        self.assertEqual('foo@example.com', doc.user.email)
        self.assertFalse(hasattr(doc.user, 'password'))
        self.assertTrue(doc.user.external_auth)
        self.assertTrue(doc.user.is_admin)
        self.assertTrue(doc.user.can_create)

    def testDelete(self):
        handle = self.getRbuildHandle()

        _user = mock.MockObject()
        mock.mockMethod(handle.facade.rbuilder.getUsers)
        mock.mockMethod(handle.ui.warning)
        handle.facade.rbuilder.getUsers._mock.setReturn([_user],
            user_name='foo')
        handle.facade.rbuilder.getUsers._mock.setReturn(None,
            user_name='bar')

        handle.Users.delete('foo')
        _user.delete._mock.assertCalled()

        handle.Users.delete('bar')
        handle.ui.warning._mock.assertCalled("No user 'bar' found")
