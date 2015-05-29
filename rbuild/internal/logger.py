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

    def debug(self, msg, *args):
        self._write(msg, 'DEBUG: ', *args)

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
