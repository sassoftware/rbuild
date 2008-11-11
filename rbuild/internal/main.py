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

Example::
    from rbuild.internal import main
    rv = main.main(['rbuild', 'build', 'packages'])
    sys.exit(rv)
"""

import errno
import re
import sys

from conary.build import explain
from conary.lib import log
from conary.lib import mainhandler
from conary import errors as conaryerrors

from rmake import errors as rmakeerrors

from rbuild import handle
from rbuild import constants
from rbuild import errors
from rbuild import rbuildcfg
from rbuild.internal import pluginloader
from rbuild.internal import helpcommand
from rbuild.pluginapi import command

if 'BaseException' not in __builtins__:
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

    def __init__(self, *args, **kw):
        mainhandler.MainHandler.__init__(self, *args, **kw)
        self.plugins = None
        self.handle = None

    def getCommand(self, argv, cfg):
        """
        Initializes plugins so that all commands are available,
        then returns the correct command based on argv.

        @param argv: Argument vector as provided by C{sys.argv}
        @param cfg: An C{RbuildConfiguration} object
        @return: C{commandClass} instance selected by C{argv}
        """
        self.plugins = pluginloader.getPlugins(argv, cfg.pluginDirs)
        self.handle = handle.RbuildHandle(cfg, self.plugins)
        self.plugins.registerCommands(self, self.handle)
        self.plugins.initialize()
        return mainhandler.MainHandler.getCommand(self, argv, cfg)

    def _getPreCommandOptions(self, argv, cfg):
        """
        Handles flags that exist before the actual command.  These get read
        before the command is processed and thus can change things like
        the configuration options to be used when loading the commands.
        """
        argSet, args = mainhandler.MainHandler._getPreCommandOptions(self, 
                                                                argv, cfg)
        thisCommand = self.abstractCommand()
        _, cfgMap = thisCommand.prepare()
        thisCommand.processConfigOptions(cfg, cfgMap, argSet)
        return argSet, args

    def getSupportedCommands(self):
        """
        @return: C{dict} containing a mapping from name to command
        objects for all commands currently registered.
        """
        return self._supportedCommands

    def usage(self, rc=1, showAll=False):
        """
        Displays usage message
        @param rc: exit to to exit with
        @param showAll: Defaults to False.  If False, display only common
        commands, those commands without the C{hidden} attribute set to True.
        """
        print 'rbuild: Conary-based Product Development Tool'
        if not showAll:
            print
            print 'Common Commands (use "rbuild help" for the full list)'
        return mainhandler.MainHandler.usage(self, rc, showAll=showAll)

    def runCommand(self, thisCommand, _, argSet, args):
        """
        Runs the command given with the parameters expected in rbuild
        @param thisCommand: RbuildCommand subclass to run
        @param argSet: C{dict} of flags passed to this command
        @param args: C{list} of arguments to the command
        @return: C{integer} exit code to use for rbuild
        """
        #pylint: disable-msg=W0221
        # runCommand is an *args, **kw method and pylint doesn't like that
        # in the override we specify these explicitly
        cfg = self.handle.getConfig()
        if getattr(thisCommand, 'requireConfig', True) and \
           not self.handle.Config.isComplete(cfg):
            self.handle.Config.initializeConfig(cfg)
        if 'stage' in argSet:
            stageName = argSet.pop('stage')
            self.handle.productStore.setActiveStageName(stageName)

        lsprof = False
        if argSet.has_key('lsprof'):
            import cProfile
            prof = cProfile.Profile()
            prof.enable()
            lsprof = True
            del argSet['lsprof']

        rv = thisCommand.runCommand(self.handle, argSet, args)

        if lsprof:
            prof.disable()
            prof.dump_stats('rbuild.lsprof')
            prof.print_stats()

        return rv

    def _getParserFlags(self, thisCommand):
        flags = mainhandler.MainHandler._getParserFlags(self, thisCommand)

        # If thisCommand has no 'description' attribute, clean up epydoc
        # formatting from the doc string and set it as the description. 
        if not hasattr(thisCommand, 'description') or \
           thisCommand.description is None:
            docString = thisCommand.__doc__ or ''
            docStringRe = re.compile('[A-Z]\{[^{}]*\}')
            srch = re.search(docStringRe, docString)
            while srch:
                oldString = srch.group()
                newString = explain._formatString(oldString)
                docString = docString.replace(oldString, newString)
                srch = re.search(docStringRe, docString)
            # override the description returned from the super method with
            # this new one.
            flags['description'] = docString

        return flags


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
        rc =  RbuildMain().main(argv, debuggerException=debuggerException)
        if rc is None:
            return 0
        return rc
    except debuggerException, err:
        raise
    except rmakeerrors.OpenError, err:
        log.error(err.args[0] + '''

Could not contact the rMake server.  Perhaps the rMake service is not
running.  To start the rMake service, as root, try running the command:
service rmake restart''')
        return 1
    except (errors.BaseError, conaryerrors.ConaryError, conaryerrors.ParseError,
            conaryerrors.CvcError, rmakeerrors.RmakeError), err:
        log.error(err)
        return 1
    except IOError, e:
        # allow broken pipe to exit
        if e.errno != errno.EPIPE:
            raise
    except KeyboardInterrupt:
        return 1
    return 0
