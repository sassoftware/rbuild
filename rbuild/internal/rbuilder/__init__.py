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
import os

from conary.lib import options
from conary.lib.cfg import ConfigFile
from conary import errors as conaryerrors
from conary.lib.cfgtypes import CfgPathList
from conary.lib import mainhandler
from conary.lib import log

from rmake import errors as rmakeerrors

from rbuild import errors
from rbuild import handle
from rbuild.internal import helpcommand
from rbuild.internal import main as rbuild_main
from rbuild.internal.rbuilder import config, projectadd, usercreate, buildcmds, refs

(NO_PARAM,  ONE_PARAM)  = (options.NO_PARAM, options.ONE_PARAM)
(OPT_PARAM, MULT_PARAM) = (options.OPT_PARAM, options.MULT_PARAM)

class RBuilderShellConfig(ConfigFile):
    serverUrl =  None

    def __init__(self, readConfigFiles = True):
        ConfigFile.__init__(self)
        if readConfigFiles:
            self.readFiles()

    def readFiles(self):
        if os.environ.has_key("HOME"):
            fn = '/'.join((os.environ["HOME"], ".rbuilderrc"))
            self.read(fn, exception=False)

class RBuilderMain(rbuild_main.RbuildMain):
    ''''''
    name = 'rbuilder'
    commandList = [helpcommand.HelpCommand,
        config.RbuilderConfigCommand,
        projectadd.RbuilderProjectAddCommand,
        usercreate.RbuilderUserCreateCommand,
        buildcmds.RbuilderBuildURLCommand,
        buildcmds.RbuilderBuildWaitCommand,
        buildcmds.RbuilderBuildProjectCommand,
        buildcmds.RbuilderBuildCreateCommand,
        #refs.RbuilderReferencesCommand,
    ]

    def getCommand(self, argv, cfg):
        #Skip the plugin loading: we don't want the noise
        self.handle = handle.RbuildHandle(cfg, self.plugins)
        return mainhandler.MainHandler.getCommand(self, argv, cfg)

    def usage(self, rc=1, showAll=False):
        """
        Displays usage message
        @param rc: exit to to exit with
        @param showAll: Defaults to False.  If False, display only common
        commands, those commands without the C{hidden} attribute set to True.
        """
        print \
'''rbuilder: command-line interface to an rBuilder Server

    WARNING: This command is deprecated in favor of using rbuild and product
    definitions'''

        if not showAll:
            print
            print 'Common Commands (use "rbuilder help" for the full list)'
        return mainhandler.MainHandler.usage(self, rc, showAll=showAll)

def main(argv=None):
    """
    Python hook for starting rbuild from the command line.
    """
    return rbuild_main._main(argv, RBuilderMain)
