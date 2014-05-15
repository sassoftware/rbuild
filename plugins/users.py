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
users
'''
from xobj import xobj

from rbuild import errors
from rbuild import pluginapi
from rbuild.pluginapi import command


class CreateUserCommand(command.BaseCommand):
    help = 'Create a new rbuilder user'
    paramHelp = '[options]'
    docs = {
        'user-name': "Name used for login",
        'full-name': "User's full name",
        'email': "User's email address",
        'password': "User's password",
        'external': 'Use external authentication service',
        'admin': 'User is an admin',
        'create-resources': 'User has create resources permissions',
        }

    def addLocalParameters(self, argDef):
        argDef['user-name'] = command.ONE_PARAM
        argDef['full-name'] = command.ONE_PARAM
        argDef['email'] = command.ONE_PARAM
        argDef['password'] = command.ONE_PARAM
        argDef['external'] = command.NO_PARAM
        argDef['admin'] = command.NO_PARAM
        argDef['create-resources'] = command.NO_PARAM

    def runCommand(self, handle, argSet, args):
        ui = handle.ui

        self.requireParameters(args)

        # user_name, full_name and email are required
        kwargs = dict(
            user_name=argSet.get('user-name', ui.getResponse('User name')),
            full_name=argSet.get('full-name', ui.getResponse('Full name')),
            email=argSet.get('email', ui.getResponse('Email')),
            )

        # must select external authentication or provide a password
        if 'external' in argSet:
            kwargs['external_auth'] = argSet['external']
        else:
            kwargs['password'] = argSet.pop('password',
                ui.getPassword('Password'))

        if 'admin' in argSet:
            kwargs['is_admin'] = argSet['admin']

        if 'create-resources' in argSet:
            kwargs['can_create'] = argSet['create-resources']

        handle.Users.create(**kwargs)


class DeleteUsersCommand(command.BaseCommand):
    help = 'Delete an rbuilder user'
    paramHelp = '<username>+'

    def runCommand(self, handle, argSet, args):
        _, usernames = self.requireParameters(args, expected='USERNAME',
            appendExtra=True)

        for user in usernames:
            if handle.ui.getYn("Really delete user '%s'" % user, False):
                handle.Users.delete(user)


class EditUserCommand(command.BaseCommand):
    help = 'Edit an existing rbuilder user'
    paramHelp = '[options] <username>'
    docs = {
        'full-name': "User's full name",
        'email': "User's email address",
        'password': "User's password",
        'external': 'Turn on external authentication',
        'no-external': 'Turn off external authentication',
        'admin': 'Turn on administrative privlidges',
        'no-admin': 'Turn off administrative privlidges',
        'create-resources': 'Turn on create resources permissions',
        'no-create-resources': 'Turn off create resources permissions',
        }

    def addLocalParameters(self, argDef):
        argDef['full-name'] = command.OPT_PARAM
        argDef['email'] = command.OPT_PARAM
        argDef['password'] = command.OPT_PARAM
        argDef['external'] = command.NO_PARAM
        argDef['no-external'] = command.NO_PARAM
        argDef['admin'] = command.NO_PARAM
        argDef['no-admin'] = command.NO_PARAM
        argDef['create-resources'] = command.NO_PARAM
        argDef['no-create-resources'] = command.NO_PARAM

    def runCommand(self, handle, argSet, args):
        ui = handle.ui
        _, user_name = self.requireParameters(args, expected='USERNAME')

        user = handle.facade.rbuilder.getUsers(user_name=user_name)
        if user:
            user = user[0]
        else:
            raise errors.BadParameterError("No user '%s' found" % user_name)

        kwargs = {}
        if 'full-name' in argSet:
            full_name = argSet.get('full-name')
            if full_name is True:
                full_name = ui.getResponse('Full name', default=user.full_name)
            kwargs['full_name'] = full_name

        if 'email' in argSet:
            email = argSet.get('email')
            if email is True:
                email = ui.getResponse('Email', default=user.email)
            kwargs['email'] = email

        if 'external' in argSet or 'no-external' in argSet:
            kwargs['external_auth'] = (argSet.get('external', False)
                and not argSet.get('no-external', False))

        if 'admin' in argSet or 'no-admin' in argSet:
            kwargs['is_admin'] = (argSet.get('admin', False)
                and not argSet.get('no-admin', False))

        if 'create-resources' in argSet or 'no-create-resources' in argSet:
            kwargs['can_create'] = (argSet.get('create-resources', False)
                and not argSet.get('no-create-resources', False))

        if 'password' in argSet:
            if kwargs.get('external_auth'):
                # user tried to set both password and external auth
                raise errors.BadParameterError("Cannot use external"
                    " authentication and provide a password")
            password = argSet.get('password')
            if password is True:
                password = ui.getPassword('Password')
            kwargs['password'] = password

        handle.Users.edit(user, **kwargs)


class ListUsersCommand(command.ListCommand):
    help = 'List rbuilder users'
    paramHelp = '<username>+'

    resource = 'users'
    listFields = ('user_id', 'user_name', 'full_name', 'email', 'is_admin',
        'external_auth', 'can_create')
    showFieldMap = dict(
        created_by=dict(accessor=lambda u: u.created_by.full_name),
        roles=dict(accessor=lambda u: ', '.join(sorted(r.name for r in u.roles))),
        modified_by=dict(accessor=lambda u: u.modified_by.full_name),
        )


class Users(pluginapi.Plugin):
    name = 'users'

    def create(self, user_name, full_name, email, password=None,
            external_auth=False, is_admin=False, can_create=False):
        '''Create a rbuilder user

        :param user_name: login name for user
        :type user_name: str
        :param full_name: full name of the user
        :type full_name: str
        :param email: user's email address
        :type email: str
        :param password: user's password, if not using external authentication
        :type password: str
        :param external_auth: whether to use external auth, must not be True if
            password is provided
        :type external_auth: bool
        :param is_admin: is this an admin user
        :type is_admin: bool
        :param can_create: can this user create resources
        :type can_create: bool
        :raises: rbuild.errors.PluginError
        '''
        if external_auth and password:
            raise errors.PluginError('Cannot use a password with external'
                ' authentication')

        if not external_auth and not password:
            raise errors.PluginError('Must provide a password if not using'
                ' external authentication')

        # create the user xml document
        user_doc = xobj.Document()
        user_doc.user = user = xobj.XObj()
        user.user_name = user_name
        user.full_name = full_name
        user.email = email
        if password is not None:
            user.password = password
        user.external_auth = external_auth
        user.is_admin = is_admin
        user.can_create = can_create

        # POST the new user
        client = self.handle.facade.rbuilder._getRbuilderRESTClient()
        client.api.users.append(user_doc)

    def delete(self, user_name):
        user = self.handle.facade.rbuilder.getUsers(user_name=user_name)
        if user:
            user[0].delete()
        else:
            self.handle.ui.warning("No user '%s' found" % user_name)

    def edit(self, user, full_name=None, email=None, password=None,
            external_auth=None, is_admin=None, can_create=None):
        '''Change fields on an existing user. None values are assuemd to be
        unchanged fields.

        :param user: user to be editted
        :type user: robj(user)
        :param full_name: the user's full name, used for displayConfig
        :type full_name: str or None
        :param email: user's email address
        :type email: str or None
        :param password: user's password
        :type password: str or None
        :param external_auth: whether to use external authentication
        :type external_auth: bool or None
        :param is_admin: whether this user is an administratior
        :type is_admin: bool or None
        :param can_create: whether this user can create resources
        :type can_create: bool or None
        :raises: rbuild.errors.PluginError
        '''
        if external_auth and password:
            raise errors.PluginError('Cannot set a password and use external'
                ' authentication')

        if full_name is not None:
            user.full_name = full_name

        if email is not None:
            user.email = email

        if password is not None:
            user.password = password

        if external_auth is not None:
            user.external_auth = external_auth

        if is_admin is not None:
            user.is_admin = is_admin

        if can_create is not None:
            user.can_create = can_create

        # hack because rbuilder gives us dates in a format it can't parse
        user.modified_date = ''
        user.created_date = ''
        user.last_login_date = ''

        # save the user
        user.persist()

    def initialize(self):
        for command, subcommand, command_class in (
                ('create', 'user', CreateUserCommand),
                ('delete', 'users', DeleteUsersCommand),
                ('edit', 'user', EditUserCommand),
                ('list', 'users', ListUsersCommand),
                ):
            cmd = self.handle.Commands.getCommandClass(command)
            cmd.registerSubCommand(subcommand, command_class)

    def list(self, *args, **kwargs):
        return self.handle.facade.rbuilder.getUsers(**kwargs)

    def show(self, user_name):
        user = self.handle.facade.rbuilder.getUsers(user_name=user_name)
        if user:
            return user[0]
