#
# Copyright (c) 2005-2008 rPath, Inc.
#
# This program is distributed under the terms of the Common Public License,
# version 1.0. A copy of this license should have been distributed with this
# source file in a file called LICENSE. If it is not present, the license
# is always available at http://www.rpath.com/permanent/licenses/CPL-1.0.
#
# This program is distributed in the hope that it will be useful, but
# without any warranty; without even the implied warranty of merchantability
# or fitness for a particular purpose. See the Common Public License for
# full details.
#

import sys
from rbuild import errors
from rbuild.facade import rbuilderfacade
from rbuild.internal.rbuilder import rbuildercommand
from rbuild.pluginapi import command


class RbuilderUserCreateCommand(rbuildercommand.RbuilderCommand):
    """
    Create a new user on your rbuilder.  This method requires that your user
    credentials have rbuilder administration rights.
    """

    commands = ['user-create']
    help = 'Create a new user (requires admin rights)'
    paramHelp = '<username> <email>'
    docs = { 
            'password': 'Specify a password instead of prompting',
            'full-name': 'The full name of the user' }
    requireConfig = False

    def addLocalParameters(self, argDef):
        argDef['password'] = command.ONE_PARAM
        argDef['full-name'] = command.ONE_PARAM

    #pylint: disable-msg=R0201,R0903
    # could be a function, and too few public methods
    def runCommand(self, handle, argSet, args):
        args = args[2:]
        if len(args) != 2:
            return self.usage()

        username, email = args

        pw1 = argSet.pop('password', None)
        fullName = argSet.pop('full-name', '')

        if not pw1 and sys.stdin.isatty():
            from getpass import getpass

            pw1 = getpass('New password:')
            pw2 = getpass('Reenter password:')

            if pw1 != pw2:
                raise errors.RbuildError('Passwords do not match')
        elif not pw1:
            # chop off the trailing newline
            pw1 = sys.stdin.readline()[:-1]

        userId = handle.facade.rbuilder.createUser(username, email, pw1, fullName)

        print "User %s created (id %d)" % (username, userId)

        return 0

