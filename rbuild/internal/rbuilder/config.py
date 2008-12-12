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
from rbuild import pluginapi
from rbuild.internal.rbuilder import rbuildercommand
from rbuild.pluginapi import command


class RbuilderConfigCommand(rbuildercommand.RbuilderCommand):
    """
    Dumps the current configuration
    """

    commands = ['config']
    help = 'Dumps the current configuration for this rbuilder client'
    docs = {'show-passwords': 'do not mask passwords'}
    requireConfig = False

    def addLocalParameters(self, argDef):
        argDef['show-passwords'] = command.NO_PARAM

    #pylint: disable-msg=R0201,R0903
    # could be a function, and too few public methods
    def runCommand(self, handle, argSet, args):
        if len(args) > 2:
            return self.usage()

        showPasswords = argSet.pop('show-passwords', False)
        try:
            prettyPrint = sys.stdout.isatty()
        except AttributeError:
            prettyPrint = False
        cfg = handle.getConfig()
        cfg.setDisplayOptions(hidePasswords = not showPasswords,
            prettyPrint = prettyPrint)
        cfg.display()

