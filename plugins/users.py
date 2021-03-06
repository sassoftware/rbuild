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
import re

from robj import errors as robj_errors

from rbuild import errors
from rbuild import pluginapi
from rbuild.pluginapi import command


# simple email validator. just verify that address contains
# only one @ sign and at least one . in the domain
EMAIL_RE = re.compile("[^@]+@[^@]+\.[^@]+")


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
        argDef['no-create'] = command.NO_PARAM

    def runCommand(self, handle, argSet, args):
        ui = handle.ui

        self.requireParameters(args)

        # user_name, full_name and email are required
        user_name = argSet.pop('user-name', None)
        if not user_name:
            user_name = ui.getResponse('User name', required=True)
        full_name = argSet.pop('full-name', None)
        if not full_name:
            full_name = ui.getResponse('Full name', required=True)
        email = argSet.pop('email', None)
        if not email:
            email = ui.getResponse('Email', required=True,
                validationFn=handle.Users.isEmail)
        else:
            if not handle.Users.isEmail(email):
                raise errors.BadParameterError(
                    "'%s' is not a valid email" % email)

        kwargs = dict(user_name=user_name, full_name=full_name, email=email)

        # must select external authentication or provide a password
        if 'external' in argSet:
            kwargs['external_auth'] = argSet['external']
        else:
            password = argSet.pop('password', None)
            if not password:
                password = ui.getPassword('Password', verify=True)
            kwargs['password'] = password

        if 'admin' in argSet:
            kwargs['is_admin'] = argSet['admin']

        if 'no-create' in argSet:
            kwargs['can_create'] = not argSet['no-create']

        try:
            handle.Users.create(**kwargs)
        except robj_errors.HTTPConflictError:
            raise errors.BadParameterError(
                "a user '%s' already exists" % user_name)


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
        'create': 'Turn on create resources permissions',
        'no-create': 'Turn off create resources permissions',
        }

    def addLocalParameters(self, argDef):
        argDef['full-name'] = command.OPT_PARAM
        argDef['email'] = command.OPT_PARAM
        argDef['password'] = command.OPT_PARAM
        argDef['external'] = command.NO_PARAM
        argDef['no-external'] = command.NO_PARAM
        argDef['admin'] = command.NO_PARAM
        argDef['no-admin'] = command.NO_PARAM
        argDef['create'] = command.NO_PARAM
        argDef['no-create'] = command.NO_PARAM

    def runCommand(self, handle, argSet, args):
        ui = handle.ui
        _, user_name = self.requireParameters(args, expected='USERNAME')

        user = handle.facade.rbuilder.getUsers(user_name=user_name)
        if user:
            user = user[0]
        else:
            raise errors.BadParameterError("No user '%s' found" % user_name)

        # common option validation
        for flag, noflag in (
                ('external', 'no-external'),
                ('admin', 'no-admin'),
                ('create', 'no-create'),
                ):
            if flag in argSet and noflag in argSet:
                raise errors.BadParameterError(
                    "Cannot use both '%s' and '%s'" % (flag, noflag))

        full_name = argSet.pop('full-name', None)
        email = argSet.pop('email', None)
        password = argSet.pop('password', None)

        kwargs = {}

        if 'external' in argSet or 'no-external' in argSet:
            kwargs['external_auth'] = (argSet.pop('external', False)
                and not argSet.pop('no-external', False))

        if 'admin' in argSet or 'no-admin' in argSet:
            kwargs['is_admin'] = (argSet.pop('admin', False)
                and not argSet.pop('no-admin', False))

        if 'create' in argSet or 'no-create' in argSet:
            kwargs['can_create'] = (argSet.pop('create', False)
                and not argSet.pop('no-create', False))

        if password and kwargs.get('external_auth'):
            # user tried to set both password and external auth
            raise errors.BadParameterError("Cannot use external"
                " authentication and provide a password")

        query_all = not kwargs and (full_name is None
            and email is None
            and password is None)

        if full_name is True or query_all:
            kwargs['full_name'] = ui.getResponse('Full name',
                default=user.full_name)
        elif full_name is not None:
            kwargs['full_name'] = full_name

        if email is True or query_all:
            kwargs['email'] = ui.getResponse('Email', default=user.email,
                validationFn=handle.Users.isEmail)
        elif email is not None:
            if not handle.Users.isEmail(email):
                raise errors.BadParameterError("'%s' is not a valid email" %
                    email)
            kwargs['email'] = email

        if (password is True
                or kwargs.get('external_auth') is False
                or query_all):
            password = ui.getPassword('New password', verify=True)
            kwargs['password'] = password
        elif password is not None:
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
        roles=dict(
            accessor=lambda u: ', '.join(sorted(r.name for r in u.roles))),
        modified_by=dict(accessor=lambda u: u.modified_by.full_name),
        )


class Users(pluginapi.Plugin):
    name = 'users'

    def create(self, user_name, full_name, email, password=None,
            external_auth=False, is_admin=False, can_create=True):
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
            password is provided, default False
        :type external_auth: bool
        :param is_admin: is this an admin user, default False
        :type is_admin: bool
        :param can_create: can this user create resources, default True
        :type can_create: bool
        :raises: rbuild.errors.PluginError
        '''
        if external_auth and password:
            raise errors.PluginError('Cannot use a password with external'
                ' authentication')

        if not external_auth and not password:
            raise errors.PluginError('Must provide a password if not using'
                ' external authentication')

        if is_admin and not self.handle.facade.rbuilder.isAdmin():
            raise errors.UnauthorizedActionError('grant admin privilege')

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
            if is_admin and not self.handle.facade.rbuilder.isAdmin():
                raise errors.UnauthorizedActionError('grant admin privilege')
            user.is_admin = is_admin

        if can_create is not None:
            if not self.handle.facade.rbuilder.isAdmin():
                raise errors.UnauthorizedActionError(
                    'toggle can create resources')
            user.can_create = can_create

        # hack because rbuilder gives us dates in a format it can't parse
        user.modified_date = ''
        user.created_date = ''
        user.last_login_date = ''

        # save the user
        user.persist()

    def initialize(self):
        for commandName, subcommand, command_class in (
                ('create', 'user', CreateUserCommand),
                ('delete', 'users', DeleteUsersCommand),
                ('edit', 'user', EditUserCommand),
                ('list', 'users', ListUsersCommand),
                ):
            cmd = self.handle.Commands.getCommandClass(commandName)
            cmd.registerSubCommand(subcommand, command_class)

    def isEmail(self, value):
        return EMAIL_RE.match(value) is not None

    def list(self, *args, **kwargs):
        return self.handle.facade.rbuilder.getUsers(**kwargs)

    def show(self, user_name):
        user = self.handle.facade.rbuilder.getUsers(user_name=user_name)
        if user:
            return user[0]
