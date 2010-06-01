#
# Copyright (c) 2008-2010 rPath, Inc.
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
"""
User interface module for rbuild.
"""
import getpass
import os
import sys
import time

from rbuild import errors
from rbuild.internal import logger

class UserInterface(object):
    def __init__(self, cfg, outStream=None, errorStream=None,
                 logRoot=None):
        if outStream is None:
            outStream = sys.stdout
        if errorStream is None:
            errorStream = sys.stderr
        self.outStream = outStream
        self.errorStream = errorStream
        self.cfg = cfg
        self._log = None
        self._logRoot = logRoot
        self.resetLogFile(logRoot)

    def resetLogFile(self, logRoot):
        '''
        Closes the current log (if any), opening a new log under
        the directory C{logRoot} unless logRoot evaluates to C{False}.
        The C{logRoot} directory will be created (if possible) if
        it does not already exist.
        If the old log path is different from the current log path,
        a message noting the continuation will be written to the
        current log before closing it.
        @param logRoot: directory into which to put log file, or
        C{False} to disable logging.
        '''
        if self._log and logRoot and logRoot != self._logRoot:
            self._log('Command log continued in %s/log', logRoot)

        if logRoot:
            self._logRoot = logRoot

        if self._log and not logRoot:
            del self._log

        if not logRoot:
            self._log = None
            return

        try:
            if not os.path.exists(logRoot):
                os.mkdir(logRoot, 0700)
            elif not os.access(logRoot, os.W_OK):
                self._log = None
                return
        except:
            # fall back gracefully if we can't create the directory
            self._log = None
            return

        self._log = logger.Logger(logRoot + '/log')
        
    def write(self, msg='', *args):
        self.outStream.write('%s\n' % (msg % args, ))
        if self._log:
            self._log(msg, *args)

    def pushContext(self, msg='', *args):
        if self._log:
            self._log.pushContext(msg, *args)

    def popContext(self, *args):
        if self._log:
            self._log.popContext(*args)

    def writeError(self, errorMsg, *args):
        self.errorStream.write('warning: %s\n' % (errorMsg % args, ))

    def writeProgress(self, msg='', *args):
        timeStamp = time.ctime(time.time())
        self.outStream.write('[%s] %s\n' % (timeStamp, msg % args))

    def info(self, msg, *args):
        if not self.cfg.quiet:
            self.write(msg, *args)
        elif self._log:
            # self.write() already logs, so do this only in quiet mode
            self._log(msg, *args)

    def warning(self, msg, *args):
        self.writeError(msg, *args)
        if self._log:
            self._log.warn(msg, *args)

    def progress(self, msg, *args):
        '''
        Writes progress message; used to indicate that a potentially
        long-running operation has been started, unless quiet mode
        has been selected in the configuration.  This is intended to
        be overrideable in different UIs in ways that could include
        not displaying the message at all or display it only transiently
        while the operation is underway.  This method should not
        be used to display important information that should not be
        missed by the user.
        @param msg: printf-style string
        @param args: printf-style variable arguments
        '''
        if not self.cfg.quiet:
            self.writeProgress(msg, *args)
        if self._log:
            self._log(msg, *args)

    def input(self, prompt):
        try:
            return raw_input(prompt)
        except EOFError:
            raise errors.RbuildError(
                    "Ran out of input while reading for '%s'" % prompt)

    def inputPassword(self, prompt):
        return getpass.getpass(prompt)

    def getPassword(self, prompt, default=None, validationFn=None):
        defaultvis = '<obscured>'
        ret = self.getResponse(prompt, default=defaultvis,
                                validationFn=validationFn,
                                inputFn=self.inputPassword)
        if ret == defaultvis:
            return default
        else:
            return ret


    def getYn(self, prompt, default=True):
        '''
        Get a yes/no response from the user.  Return a bool representing
        the user's choice.  Note that any "yes" response is always True,
        and any "no" response is always false, whether or not it is the
        default.  C{ui.getYn('really?', False)} will return False if the
        user presses return or enters C{N}.

        @param prompt: string to display
        @type prompt: str
        @param default: default value: True for yes, False for no
        @type default: bool
        @return: True for yes, False for no
        @rtype: bool
        '''
        if default:
            defaultChar = 'Y'
        else:
            defaultChar = 'N'
        response = self.getResponse(prompt, default=defaultChar)
        return response[0].upper() == 'Y'

    def getResponse(self, prompt, default=None, validationFn=None,
                    inputFn=None):
        if inputFn is None:
            inputFn = self.input
        if default:
            prompt += ' (Default: %s): ' % default
        else:
            prompt += ': '
        while True:
            response = inputFn(prompt)
            if not response:
                if not default:
                    self.write('Empty response not allowed.')
                    continue
                else:
                    return default
            if validationFn is not None:
                if not validationFn(response):
                    continue
            return response
