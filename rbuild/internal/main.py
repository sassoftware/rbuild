#
# Copyright (c) rPath, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#


"""
Implements the main() method used for starting rbuild from the command line.

Example::
    from rbuild.internal import main
    rv = main.main(['rbuild', 'build', 'packages'])
    sys.exit(rv)
"""

import errno
import getpass
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
    setSysExcepthook = False

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
        self.handle.ui.pushContext('rBuild %s: %s',
                                   self.version, ' '.join(argv))
        self.plugins.registerCommands(self, self.handle)
        self.plugins.initialize()
        return mainhandler.MainHandler.getCommand(self, argv, cfg)

    def _getPreCommandOptions(self, argv, cfg):
        #pylint: disable-msg=C0999
        # internal interface
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

    def _getUsageByClass(self, commandClass, commandName=None):
        # Copied in from conary's MainHandler class to add multiple argument
        # possiblities
        assert self.name, 'You must define the "name" attribute for class "%s"' % self.__class__.__name__
        if not commandName:
            if hasattr(commandClass, 'name'):
                commandName = commandClass.name
            else:
                commandName = commandClass.commands[0]

        # ---Begin modifications ---
        if isinstance(commandClass.paramHelp, str):
            params = [commandClass.paramHelp]
        else:
            params = commandClass.paramHelp
        commandUsage = []
        for param in params:
            commandUsage.append('%s %s %s' % (self.name, commandName, param))
        return '\n   or: '.join(commandUsage)


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
        if cfg.user and cfg.user[0] and not cfg.user[1]:
            passwd = self._promptPassword(cfg)
            cfg.setPassword(passwd)

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

        try:
            rv = thisCommand.runCommand(self.handle, argSet, args)
            self.handle.ui.popContext('Command returned %r', rv)
        except Exception, e:
            # Save this exception to re-raise
            exc_info = sys.exc_info()
            # Try to log the exception, but do not blow up if the UI has
            # failed in an unexpected way
            try:
                self.handle.ui.popContext('Command failed with exception %r', e)
            except:
                pass
            raise e, None, exc_info[2]


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

    def _promptPassword(self, cfg):
        keyDesc = 'rbuild:user:%s:%s' % (cfg.user[0], cfg.serverUrl)
        try:
            import keyutils
            keyring = keyutils.KEY_SPEC_SESSION_KEYRING
        except ImportError:
            keyutils = keyring = None
        if keyutils:
            keyId = keyutils.request_key(keyDesc, keyring)
            if keyId is not None:
                passwd = keyutils.read_key(keyId)
                if self.handle.facade.rbuilder.validateCredentials(cfg.user[0],
                        passwd, cfg.serverUrl):
                    return passwd
                # Fall through if the cached creds are invalid
        for x in range(3):
            self.handle.ui.write('Please enter the password for user %r on %s'
                    % (cfg.user[0], cfg.serverUrl))
            passwd = getpass.getpass("Password: ")
            if self.handle.facade.rbuilder.validateCredentials(cfg.user[0],
                    passwd, cfg.serverUrl):
                if keyutils:
                    keyutils.add_key(keyDesc, passwd, keyring)
                return passwd
            if not passwd:
                # User wants out but getpass eats Ctrl-C
                break
            self.handle.ui.write("The specified credentials were not valid.")
            self.handle.ui.write()
        sys.exit("Unable to authenticate to the rBuilder")


def _main(argv, MainClass):
    """
    Python hook for starting rbuild from the command line.
    @param argv: standard argument vector
    """
    if argv is None:
        argv = sys.argv
    #pylint: disable-msg=E0701
    # pylint complains about except clauses here because we sometimes
    # redefine debuggerException
    debuggerException = Exception
    try:
        argv = list(argv)
        debugAll = '--debug-all' in argv
        if debugAll:
            argv.remove('--debug-all')
        else:
            debuggerException = errors.RbuildInternalError
        sys.excepthook = errors.genExcepthook(debug=debugAll,
                                              debugCtrlC=debugAll)
        rc =  MainClass().main(argv, debuggerException=debuggerException)
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
    except (errors.RbuildBaseError, conaryerrors.ConaryError,
            conaryerrors.ParseError,
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

def main(argv=None):
    """
    Python hook for starting rbuild from the command line.
    @param argv: standard argument vector
    """
    return _main(argv, RbuildMain)
