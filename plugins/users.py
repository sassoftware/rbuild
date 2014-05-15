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
    paramHelp = '[options] <username> <full name> <email>'
    docs = {
        'external': 'Use external authentication service',
        'admin': 'User is an admin',
        'create-resources': 'User has create resources permissions',
        'password': 'User password',
        }

    def addLocalParameters(self, argDef):
        argDef['external'] = '-e', command.NO_PARAM
        argDef['admin'] = '-a', command.NO_PARAM
        argDef['create-resources'] = '-c', command.NO_PARAM
        argDef['password'] = '-p', command.ONE_PARAM

    def runCommand(self, handle, argSet, args):
        _, user_name, full_name, email = self.requireParameters(args, expected=[
                'USERNAME',
                'FULL_NAME',
                'EMAIL',
                ])

        isExternal = argSet.pop('external', False)
        isAdmin = argSet.pop('admin', False)
        createResources = argSet.pop('create-resources', False)
        password = argSet.pop('password', None)

        if password and isExternal:
            raise errors.BadParameterError("Cannot use external authentication"
                " and provide a password")

        if not password and not isExternal:
            password = handle.ui.getPassword('Password')

        handle.Users.create(user_name, full_name, email, password, isExternal,
            isAdmin, createResources)


class DeleteUsersCommand(command.BaseCommand):
    help = 'Delete an rbuilder user'
    paramHelp = '<username>+'

    def runCommand(self, handle, argSet, args):
        _, usernames = self.requireParameters(args, expected='USERNAME',
            appendExtra=True)

        for user in usernames:
            if handle.ui.getYn("Really delete user '%s'" % user, False):
                handle.Users.delete(user)

class EditUserComand(command.BaseCommand):
    pass


class ListUsersCommand(command.ListCommand):
    help = 'List rbuilder users'
    paramHelp = '<username>+'

    resource = 'users'
    listFields = ('user_id', 'user_name', 'full_name', 'email', 'is_admin',)
    showFieldMap = dict(
        created_by=dict(accessor=lambda u: u.created_by.full_name),
        roles=dict(accessor=lambda u: ', '.join(sorted(r.name for r in u.roles))),
        modified_by=dict(accessor=lambda u: u.modified_by.full_name),
        )


class Users(pluginapi.Plugin):
    name = 'users'

    def initialize(self):
        for command, subcommand, command_class in (
                ('create', 'user', CreateUserCommand),
                ('list', 'users', ListUsersCommand),
                ):
            cmd = self.handle.Commands.getCommandClass(command)
            cmd.registerSubCommand(subcommand, command_class)

    def create(self, user_name, full_name, email, password, isExternal=False,
            isAdmin=False, createResources=False):
        '''
        Create a rbuilder user

        :param user_name: login name for user
        :type user_name: str
        :param full_name: full name of the user
        :type full_name: str
        :param email: user's email address
        :type email: str
        :param password: user's password, if not using external authentication
        :type password: str
        :param isExternal: whether to use external auth, must not be True if
            password is provided
        :type isExternal: bool
        :param isAdmin: is this an admin user
        :type isAdmin: bool
        :param createResources: can this user create resources
        :type createResources: bool
        '''
        if isExternal and password:
            raise errors.PluginError('Cannot use a password with external'
                ' authentication')

        if not isExternal and not password:
            raise errors.PluginError('Must provide a password if not using'
                ' external authentication')


        # create the user xml document
        user_doc = xobj.Document()
        user_doc.user = user = xobj.XObj()
        user.user_name = user_name
        user.full_name = full_name
        user.password = password
        user.email = email
        user.external_auth = isExternal
        user.is_admin = isAdmin
        user.can_create = createResources

        # POST the new user
        client = self.handle.facade.rbuilder._getRbuilderRESTClient()
        client.api.users.append(user_doc)

    def list(self, *args, **kwargs):
        return self.handle.facade.rbuilder.getUsers(**kwargs)

    def show(self, user_name):
        user = self.handle.facade.rbuilder.getUsers(user_name=user_name)
        if user:
            return user[0]
