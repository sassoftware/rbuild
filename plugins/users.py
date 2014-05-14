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
import time

from rbuild import errors
from rbuild import pluginapi
from rbuild.pluginapi import command


class CreateUserCommand(command.BaseCommand):
    pass


class DeleteUsersCommand(command.BaseCommand):
    pass


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
        for command, command_class in (
                ('list', ListUsersCommand),
                ):
            cmd = self.handle.Commands.getCommandClass(command)
            cmd.registerSubCommand('users', command_class)

    def list(self, *args, **kwargs):
        return self.handle.facade.rbuilder.getUsers(**kwargs)

    def show(self, user_name):
        user = self.handle.facade.rbuilder.getUsers(user_name=user_name)
        if user:
            return user[0]
