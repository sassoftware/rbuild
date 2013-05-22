#!/usr/bin/python
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


import time

from rbuild_test import rbuildhelp

from rbuild.internal import logger
from testutils import mock

defaultTimestamps = (
    '[2010 May 14 06:49:19]',
    '[2010 May 14 06:53:16]',
    '[2010 May 14 06:53:28]',
    '[2010 May 14 07:08:04]',
    '[2010 May 14 07:08:17]',
    '[2010 May 14 07:09:03]',
    '[2010 May 14 07:09:09]',
    '[2010 May 14 07:09:18]',
    '[2010 May 14 07:09:34]',
    '[2010 May 14 07:09:43]',
    '[2010 May 14 07:09:50]',
)


class LoggerTest(rbuildhelp.RbuildHelper):
    def getLogger(self):
        self.logName = self.workDir+'/testlog'
        l = logger.Logger(self.logName)
        mockStrftime = mock.MockObject()
        mockStrftime._mock.setDefaultReturns(defaultTimestamps)
        self.mock(time, 'strftime', mockStrftime)
        return l

    def assertContents(self, *contents):
        timeIndex = 0
        fileLines = [x.strip() for x in open(self.logName).readlines()]
        for timeSet in contents:
            for line in timeSet:
                line = defaultTimestamps[timeIndex] + ' ' + line
                fileLine = fileLines.pop(0)
                self.assertEquals(line, fileLine)
            timeIndex += 1


    def testWrite(self):
        l = self.getLogger()
        l._write('a test', '')
        l._write('more\nlines', 'DEBUG: ')
        self.assertContents(
            ('a test',),
            ('DEBUG: more',
             'DEBUG: lines'))

    def testLevels(self):
        l = self.getLogger()
        l('implicit %s', 'info')
        l.info('some %s', 'info')
        l.warn('a %s', 'warning')
        l.error('an %s', 'error')
        self.assertContents(
            ('implicit info',),
            ('some info',),
            ('WARNING: a warning',),
            ('ERROR: an error',),
        )

    def testContext(self):
        l = self.getLogger()
        l('one')
        l.pushContext('foo%s', 'bar')
        l('two')
        l.pushContext('baz')
        l('three')
        l.popContext()
        l('four')
        l.popContext()
        l('five')
        l.popContext() # pop level that does not exist, be generous
        l('six')
        self.assertContents(
            ('one',),
            ('foobar',),
            ('  two',),
            ('  baz',),
            ('    three',),
            ('  four',),
            ('five',),
            ('six',),
        )

    def testAppend(self):
        l = self.getLogger()
        l('one')
        l.open(self.workDir+'/testlog')
        l('two')
        l = self.getLogger()
        # get to third timestamp...
        time.strftime()
        time.strftime()
        l('three')
        self.assertContents(
            ('one',),
            ('two',),
            ('three',),
        )


