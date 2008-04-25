#
# Copyright (c) 2008 rPath, Inc.
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
"""
Implements the main() method used for starting rbuild from the command line.

Example:
from rbuild.internal import main
rv = main.main(['rbuild', 'build', 'packages'])
sys.exit(rv)
"""

import errno
import sys

from conary.lib import log
from conary.lib import mainhandler
from conary import errors as conaryerrors


from rbuild import client
from rbuild import constants
from rbuild import errors
from rbuild import rbuildcfg
from rbuild.internal import pluginloader
from rbuild.internal import helpcommand
from rbuild.pluginapi import command

if 'BaseException' not in __builtins__.__dict__:
    #pylint: disable-msg=C0103,W0622
    BaseException = Exception

class RbuildMain(mainhandler.MainHandler):
    """
        RbuildMain loads plugins, reads configuration files from disk
        and parses command line arguments and calls the corresponding
        command object to perform the requested command.
    """
    name = 'rbuild'
    version = constants.VERSION

    abstractCommand = command.BaseCommand
    configClass = rbuildcfg.RbuildConfiguration
    commandList = [helpcommand.HelpCommand]

    useConaryOptions = False

    # this method is public.
    registerCommand = mainhandler.MainHandler._registerCommand

    def __init__(self, *args, **kw):
        mainhandler.MainHandler.__init__(self, *args, **kw)
        self.plugins = None

    def getCommand(self, argv, cfg):
        self.plugins = pluginloader.getPlugins(argv, cfg.pluginDirs)
        self.plugins.initializeCommands(self)
        return mainhandler.MainHandler.getCommand(self, argv, cfg)

    def getSupportedCommands(self):
        return self._supportedCommands

    def usage(self, rc=1, showAll=False):
        print 'rbuild: description here'
        if not showAll:
            print
            print 'Common Commands (use "rbuild help" for the full list)'
        return mainhandler.MainHandler.usage(self, rc, showAll=showAll)

    def runCommand(self, thisCommand, rbuildConfig, argSet, args):
        #pylint: disable-msg=W0221
        # runCommand is an *args, **kw method and pylint doesn't like that
        # in the override we specify these explicitly
        rbClient = client.RbuildClient(rbuildConfig, self.plugins)
        return thisCommand.runCommand(rbClient, rbuildConfig, argSet, args)


def main(argv=None):
    """
        Python hook for starting rbuild from the command line.
    """
    if argv is None:
        argv = sys.argv
    #pylint: disable-msg=E0701
    # pylint complains about except clauses here because we sometimes
    # redefine debuggerException
    debuggerException = BaseException
    try:
        argv = list(argv)
        debugAll = '--debug-all' in argv
        if debugAll:
            argv.remove('--debug-all')
        else:
            debuggerException = errors.InternalError
        sys.excepthook = errors.genExcepthook(debug=debugAll,
                                              debugCtrlC=debugAll)
        return RbuildMain().main(argv, debuggerException=debuggerException)
    except debuggerException, err:
        raise
    except (errors.BaseError, conaryerrors.ConaryError, conaryerrors.ParseError,
            conaryerrors.CvcError), err:
        log.error(err)
        return 1
    except IOError, e:
        # allow broken pipe to exit
        if e.errno != errno.EPIPE:
            raise
    except KeyboardInterrupt:
        return 1
    return 0

if __name__ == '__main__':
    main(sys.argv)
