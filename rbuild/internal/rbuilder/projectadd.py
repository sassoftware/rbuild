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
from rbuild.pluginapi import command

from rbuild.facade import rbuilderfacade

class RbuilderProjectAddCommand(command.BaseCommand):
    """
    Add a user to a product with the given privilege level
    """

    commands = ['project-add', 'product-add']
    help = 'Add a user to a product'
    paramHelp = '<username> <product shortname> <owner|developer>'
    requireConfig = False

    #pylint: disable-msg=R0201,R0903
    # could be a function, and too few public methods
    def runCommand(self, handle, argSet, args):
        args = args[2:]
        if len(args) != 3:
            return self.usage()

        username, productName, level = args

        handle.facade.rbuilder.addUserToProduct(productName, username, level)

        return 0

