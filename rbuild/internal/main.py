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

import sys

from conary.lib import cfg
from conary.lib import mainhandler
from conary import errors as conaryerrors


from rbuild import client
from rbuild import constants
from rbuild import errors
from rbuild import rbuildcfg
from rbuild.internal import pluginloader
from rbuild.internal import help
from rbuild.pluginapi import command


class RbuildMain(mainhandler.MainHandler):
    name = 'rbuild'
    version = constants.version

    abstractCommand = command.BaseCommand
    configClass = rbuildcfg.rBuildConfiguration
    commandList = [help.HelpCommand]

    useConaryOptions = False
    def main(self, argv=sys.argv, *args, **kw):
        cfg = self.getConfigFile(argv, ignoreErrors=True)
        return mainhandler.MainHandler.main(self, argv, *args, **kw)

    def getCommand(self, argv, cfg):
        self.plugins = pluginloader.getPlugins(argv, cfg.pluginDirs)
        self.plugins.initializeCommands(self)
        return mainhandler.MainHandler.getCommand(self, argv, cfg)

    def usage(self, rc=1, showAll=False):
        print 'rbuild: description here'
        if not showAll:
            print
            print 'Common Commands (use "rbuild help" for the full list)'
        return mainhandler.MainHandler.usage(self, rc, showAll=showAll)

    def runCommand(self, thisCommand, rbuildConfig, argSet, args):
        self.rbClient = client.rBuildClient(self.plugins, rbuildConfig)
        return thisCommand.runCommand(self.rbClient, rbuildConfig, argSet, args)

def main(argv):
    debuggerException = Exception
    try:
        argv = list(argv)
        debugAll = '--debug-all' in argv
        if debugAll:
            debuggerException = Exception
            argv.remove('--debug-all')
        else:
            debuggerException = errors.InternalError
        sys.excepthook = errors.genExcepthook(debug=debugAll,
                                              debugCtrlC=debugAll)
        return RbuildMain().main(argv, debuggerException=debuggerException)
    except debuggerException, err:
        raise
    except (errors.BaseError, conaryerrors.ConaryError, cfg.ParseError,
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
