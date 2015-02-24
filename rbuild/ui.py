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


"""
User interface module for rbuild.
"""
import getpass
import fcntl
import os
import struct
import sys
import termios
import time

from rbuild import errors
from rbuild.internal import logger


class UserInterface(object):
    _last_length = None

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

    def getTerminalSize(self):
        s = struct.pack('HHHH', 0, 0, 0, 0)
        fd = self.outStream.fileno() if self.outStream.isatty() else 1
        result = fcntl.ioctl(fd, termios.TIOCGWINSZ, s)
        rows, cols = struct.unpack('HHHH', result)[0:2]
        return rows, cols

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
        self.outStream.flush()
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
        self.outStream.flush()

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

    def multiLineInput(self, prompt):
        '''Reads input until it catches an EOFError, and returns a newline-
        concatenated string or the empty string if no input was received.

        :param prompt: user prompt
        :type prompt: str
        :returns: user's input
        :rtype: str
        '''
        response = None
        try:
            response = [raw_input(prompt)]
            while True:
                response.append(raw_input())
        except EOFError:
            return '\n'.join(response) if response else ''

    def inputPassword(self, prompt):
        return getpass.getpass(prompt)

    def getPassword(self, prompt, default=None, validationFn=None):
        if default:
            defaultvis = '<obscured>'
        else:
            defaultvis = None
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

        validationFn = lambda r : r[0].upper() in ['Y', 'N', ]
        response = self.getResponse(prompt, default=defaultChar, validationFn=validationFn)
        return response[0].upper() == 'Y'

    def getResponse(self, prompt, default=None, validationFn=None,
                    inputFn=None, required=False):
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
                    if required:
                        self.write('Empty response not allowed.')
                        continue
                    response = None
                elif default:
                    return default
            if validationFn is not None:
                if not validationFn(response):
                    continue
            return response

    def _getChoiceResponse(self, prompt, choices, prePrompt='', default=None,
                           pageSize=None, promptDefault=None):
        choices = list(choices)
        assert choices
        pad = len(str(len(choices)))
        if pageSize:
            pageNo = 0
            pageCount, remainder = divmod(len(choices), pageSize)
            if remainder:
                pageCount += 1
        while True:
            hasPrev = hasNext = None
            self.write(prePrompt)
            if pageSize:
                idxStart = pageNo * pageSize
                idxEnd = (pageNo + 1) * pageSize
                hasPrev = (pageNo > 0)
                chunk = ((idxStart + x, y)
                         for x, y in enumerate(choices[idxStart:idxEnd]))
            else:
                chunk = enumerate(choices)
            for n, choice in chunk:
                self.write(' %*d. %s' % (pad, n + 1, choice))
            if hasPrev:
                self.write(' %*s  %s' % (pad, '<', "(previous page)"))
            if pageSize and pageNo < pageCount - 1:
                self.write(' %*s  %s' % (pad, '>', "(next page)"))
                hasNext = True

            response = self.getResponse(
                prompt + ' [%d-%d]' % (1, len(choices)),
                default=promptDefault,
                )
            if hasPrev and response == '<':
                pageNo -= 1
                continue
            if hasNext and response == '>':
                pageNo += 1
                continue

            try:
                response = int(response)
            except (ValueError, TypeError):
                if isinstance(response, list):
                    return response
                continue
            return response

    def getChoice(self, prompt, choices, prePrompt='Choose one:', default=None,
                  pageSize=None):
        """
        Present a list of choices to the user and have them select one by
        index. Returns a 0-indexed integer into the original list of choices.

        @param prompt: string to display in the final prompt
        @type  prompt: str
        @param choices: list of items to display, in desired order
        @type  choices: list
        @param prePrompt: optional string to display before the list of choices
        @type  prePrompt: str
        @param default: index of default response
        @type  default: int
        @param pageSize: (optional) number of items per page. Defaults to no pagination.
        @type  pageSize: int
        """
        if default is None:
            promptDefault = default
        else:
            # prompts are 1-indexed
            promptDefault = default + 1

        while True:
            response = self._getChoiceResponse(
                prompt, choices, prePrompt, default, pageSize, promptDefault)
            if not (0 < response <= len(choices)):
                continue
            return response - 1

    def getChoices(self, prompt, choices, prePrompt='Choose:', default=None,
                   pageSize=None):
        """
        Present a list of choices to the user and have them select one or more
        by index. Returns a 0-indexed integer into the original list of
        choices.

        @param prompt: string to display in the final prompt
        @type  prompt: str
        @param choices: list of items to display, in desired order
        @type  choices: list
        @param prePrompt: optional string to display before the list of choices
        @type  prePrompt: str
        @param default: default choice(s)
        @type  default: list of ints
        @param pageSize: (optional) number of items per page. Defaults to no
                         pagination.
        @type  pageSize: int
        """
        promptDefault = set(d + 1 for d in default) if default else set()
        while True:
            response = self._getChoiceResponse(
                prompt, choices, prePrompt, default, pageSize,
                list(promptDefault))

            if isinstance(response, list):
                return [r - 1 for r in response]

            if not (0 < response <= len(choices)):
                continue

            # toggle response
            if response in promptDefault:
                promptDefault.discard(response)
            else:
                promptDefault.add(response)

    def promptPassword(self, keyDesc, prompt, promptDesc, validateCallback):
        try:
            import keyutils
            keyring = keyutils.KEY_SPEC_SESSION_KEYRING
        except ImportError:
            keyutils = keyring = None
        if keyutils:
            keyId = keyutils.request_key(keyDesc, keyring)
            if keyId is not None:
                passwd = keyutils.read_key(keyId)
                if validateCallback(passwd):
                    return passwd
                # Fall through if the cached creds are invalid
        for x in range(3):
            self.write(promptDesc)
            passwd = self.inputPassword(prompt)
            if validateCallback(passwd):
                if keyutils:
                    keyutils.add_key(keyDesc, passwd, keyring)
                return passwd
            if not passwd:
                # User wants out but getpass eats Ctrl-C
                break
            self.write("The specified credentials were not valid.\n")
        return None

    def lineOutProgress(self, msg, *args):
        '''
        Writes progress message; used to indicate that a potentially
        long-running operation has been started, unless quiet mode
        has been selected in the configuration, but only display it
        transiently while the operation is underway. This method should
        not be used to display important information that should not be
        missed by the user.
        @param msg: printf-style string
        @param args: printf-style variable arguments
        '''
        if not self.cfg.quiet:
            if self.outStream.isatty():
                timeStamp = time.ctime(time.time())
                length = len(msg)
                self.outStream.write('\r[%s] %s' % (timeStamp, msg % args, ))
                if length < self._last_length:
                    i = (self._last_length - length) + 1
                    self.outStream.write(' ' * i + '\b' * i)
                self.outStream.flush()
                self._last_length = length
                if self._log:
                    self._log(msg, *args)
            else:
                self.progress(msg, *args)

    def writeTable(self, rows, headers=None, padded=True):
        '''
        Writes a table; used to display data that is best displayed in rows and
        columns. If 'headers' is not provided, then we assume the first row is
        the header. Regardless, only the columns listed in the header will be
        displayed, any other elements in the rows will be ignored.

        @param rows: the data to be displayed
        @type rows: list of tuples
        @param headers: table headers
        @type headers: tuple of strings
        @param padded: pad each row element so columns are aligned
        @type padded: bool
        '''
        if headers is None:
            headers = rows.pop(0)

        columns = len(headers)
        padding = [''] * (columns - 1)
        if padded:
            padding = [len(h) for h in headers[:-1]]
            for row in rows:
                for idx, elem in enumerate(row[:columns - 1]):
                    padding[idx] = max(padding[idx], len(elem))

        # create a padded format string, but do not pad the last column
        format_string = '  '.join(
            ['{%d:%s}' % x for x in zip(range(columns - 1), padding)]
            + ['{%d:%s}' % (columns - 1, '')])

        output = format_string.format(*headers)
        self.outStream.write('%s\n' % output)
        self._log(output)

        for row in rows:
            if len(row) < columns:
                # extend row with empty strings
                row = row + ('',) * (columns - len(row))
            output = format_string.format(*row[:columns])
            self.outStream.write('%s\n' % output)
            self._log(output)
        self.outStream.flush()
