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
Implements the logger object used to keep a record of what has been done.

Example::
    from rbuild.internal import logger
    log = logger.Logger(logPath)
    log.pushContext(command) # opens indentation level
    log(string) # logs at informational level
    log.info(string)
    log.warn(warnString)
    log.error(errorString, with, format, arguments)
    log.popContext() # closes indentation level
"""

import time

class Logger(object):
    def __init__(self, logPath):
        self.logFile = None
        self.open(logPath)
        self.indent = ''

    def open(self, logPath):
        if self.logFile:
            self.logFile.close()
        self.logFile = open(logPath, 'a')

    def pushContext(self, msg, *args):
        self._write(msg, '', *args)
        self.indent += '  '

    def popContext(self, *args):
        self.indent = self.indent[:-2]
        if args:
            self.info(*args)

    def __call__(self, msg, *args):
        self.info(msg, *args)

    def info(self, msg, *args):
        self._write(msg, '', *args)

    def warn(self, msg, *args):
        self._write(msg, 'WARNING: ', *args)

    def error(self, msg, *args):
        self._write(msg, 'ERROR: ', *args)

    def _write(self, msg, level, *args):
        timestamp = time.strftime('[%Y %b %d %H:%M:%S]')
        if args:
            msg = msg % args
        for textline in msg.split('\n'):
            self.logFile.write('%s %s%s%s\n' %(
                timestamp, self.indent, level, textline))
        self.logFile.flush()
