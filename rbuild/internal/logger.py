#
# Copyright (c) 2010 rPath, Inc.
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
