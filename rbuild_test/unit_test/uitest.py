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



import getpass
import os
import StringIO
import sys
import time

from testutils import mock
from rbuild_test import rbuildhelp

from rbuild import errors
from rbuild.internal import logger

class UserInterfaceTest(rbuildhelp.RbuildHelper):

    def testWriteTable(self):
        h = self.getRbuildHandle()
        h.ui._log = mock.MockObject()

        # test single column table
        h.ui.writeTable(
            [('H1',), ('data1',)])
        h.ui.outStream.write._mock.assertCalled(('H1\n'))
        h.ui.outStream.write._mock.assertCalled(('data1\n'))
        h.ui._log._mock.assertCalled(('H1'))
        h.ui._log._mock.assertCalled(('data1'))

        # test basic table output with implicit headers
        h.ui.writeTable(
            [('H1', 'H2', 'H3'), ('data1', 'data200', 'data3', 'ignored')])
        h.ui.outStream.write._mock.assertCalled(('H1     H2       H3\n'))
        h.ui.outStream.write._mock.assertCalled(('data1  data200  data3\n'))
        h.ui._log._mock.assertCalled(('H1     H2       H3'))
        h.ui._log._mock.assertCalled(('data1  data200  data3'))

        # test basic table output with explicit headers
        h.ui.writeTable(
            [('data1', 'data200', 'data3', 'ignored')],
            headers=('H1', 'H2', 'H3'),
            )
        h.ui.outStream.write._mock.assertCalled(('H1     H2       H3\n'))
        h.ui.outStream.write._mock.assertCalled(('data1  data200  data3\n'))
        h.ui._log._mock.assertCalled(('H1     H2       H3'))
        h.ui._log._mock.assertCalled(('data1  data200  data3'))

        # validated padding
        h.ui.writeTable(
            [('data1', 'data200', 'data3', 'ignored'),
             ('data4',),
             ('', 'data5',),
             ('', '', 'data6'),
             ],
            headers=('H1', 'H2', 'H3'),
            )
        h.ui.outStream.write._mock.assertCalled(('H1     H2       H3\n'))
        h.ui.outStream.write._mock.assertCalled(('data1  data200  data3\n'))
        h.ui.outStream.write._mock.assertCalled(('data4           \n'))
        h.ui.outStream.write._mock.assertCalled(('       data5    \n'))
        h.ui.outStream.write._mock.assertCalled(('                data6\n'))
        h.ui._log._mock.assertCalled(('H1     H2       H3'))
        h.ui._log._mock.assertCalled(('data1  data200  data3'))
        h.ui._log._mock.assertCalled(('data4           '))
        h.ui._log._mock.assertCalled(('       data5    '))
        h.ui._log._mock.assertCalled(('                data6'))

        # validate no padding
        h.ui.writeTable(
            [('data1', 'data200', 'data3', 'ignored'),
             ('data4',),
             ('', 'data5',),
             ('', '', 'data6'),
             ],
            headers=('H1', 'H2', 'H3'),
            padded=False,
            )
        h.ui.outStream.write._mock.assertCalled(('H1  H2  H3\n'))
        h.ui.outStream.write._mock.assertCalled(('data1  data200  data3\n'))
        h.ui.outStream.write._mock.assertCalled(('data4    \n'))
        h.ui.outStream.write._mock.assertCalled(('  data5  \n'))
        h.ui.outStream.write._mock.assertCalled(('    data6\n'))
        h.ui._log._mock.assertCalled(('H1  H2  H3'))
        h.ui._log._mock.assertCalled(('data1  data200  data3'))
        h.ui._log._mock.assertCalled(('data4    '))
        h.ui._log._mock.assertCalled(('  data5  '))
        h.ui._log._mock.assertCalled(('    data6'))

    def testUserInterface(self):
        h = self.getRbuildHandle()
        h.ui._log = mock.MockObject()

        h.ui.warning('foo %s', 'bar')
        h.ui.errorStream.write._mock.assertCalled('warning: foo bar\n')
        h.ui._log.warn._mock.assertCalled('foo %s', 'bar')

        h.ui.info('foo %s', 'bar')
        h.ui.outStream.write._mock.assertCalled('foo bar\n')
        h.ui._log._mock.assertCalled('foo %s', 'bar')

        self.mock(time, 'ctime', lambda x: 'NOW')
        h.ui.progress('foo %s', 'bar')
        h.ui.outStream.write._mock.assertCalled('[NOW] foo bar\n')
        h.ui._log._mock.assertCalled('foo %s', 'bar')

        h.ui.lineOutProgress('foo %s', 'bar')
        h.ui.outStream.write._mock.assertCalled('\r[NOW] foo bar')

        h.ui.lineOutProgress('spam')
        h.ui.outStream.write._mock.assertCalled('\r[NOW] spam')
        h.ui.outStream.write._mock.assertCalled('   \b\b\b')

        h.ui.outStream.isatty._mock.setReturn(False)
        h.ui.lineOutProgress('foo %s', 'bar')
        h.ui.outStream.write._mock.assertCalled('[NOW] foo bar\n')

        h.ui.cfg.quiet = True
        h.ui.progress('foo %s', 'bar')
        h.ui.outStream.write._mock.assertNotCalled()
        h.ui._log._mock.assertCalled('foo %s', 'bar')

        h.ui.lineOutProgress('foo %s', 'bar')
        h.ui.outStream.write._mock.assertNotCalled()

        h.ui.info('foo %s', 'bar')
        h.ui.outStream.write._mock.assertNotCalled()
        h.ui._log._mock.assertCalled('foo %s', 'bar')

        h.ui.pushContext('foo %s', 'bar')
        h.ui.outStream.write._mock.assertNotCalled()
        h.ui._log.pushContext._mock.assertCalled('foo %s', 'bar')

        h.ui.popContext()
        h.ui.outStream.write._mock.assertNotCalled()
        h.ui._log.popContext._mock.assertCalled()

        # explicitly umock due to mocking in time
        self.unmock()

    def testNonDefaultUserInterface(self):
        ui = mock.MockObject()
        h = self.getRbuildHandle(userInterface=ui)
        self.assertEquals(h.ui, ui)

    def testResetLogFile(self):
        h = self.getRbuildHandle()
        oldLog = h.ui._log = mock.MockObject()
        mockExists = mock.MockObject()
        self.mock(os.path, 'exists', mockExists)
        mockAccess = mock.MockObject()
        self.mock(os, 'access', mockAccess)
        mockMkdir = mock.MockObject()
        self.mock(os, 'mkdir', mockMkdir)
        mockLogger = mock.MockObject()
        self.mock(logger, 'Logger', mockLogger)

        # reset with same dir, check for no continuation record
        logRoot = self.workDir + '/.rbuild'
        h.ui.resetLogFile(logRoot)
        oldLog._mock.assertNotCalled()
        h.ui._log = oldLog
        mockExists._mock.assertCalled(logRoot)
        mockMkdir._mock.assertNotCalled()
        mockAccess._mock.assertCalled(logRoot, os.W_OK)

        # reset with different dir, check for continuation record
        logRoot = self.workDir + '/new-rbuild'
        mockExists._mock.setReturn(False, logRoot)
        h.ui.resetLogFile(logRoot)
        oldLog._mock.assertCalled('Command log continued in %s/log', logRoot)
        h.ui._log = oldLog
        mockExists._mock.assertCalled(logRoot)
        mockMkdir._mock.assertCalled(logRoot, 0700)
        mockAccess._mock.assertNotCalled()

        # reset with inaccessible dir, check for failure handling
        os.path.exists._mock.raiseErrorOnAccess(IOError)
        h.ui.resetLogFile(logRoot)
        self.assertEquals(h.ui._log, None)
        h.ui._log = oldLog
        mockExists._mock.assertCalled(logRoot)
        mockMkdir._mock.assertNotCalled()
        mockAccess._mock.assertNotCalled()

        # reset with unwriteable dir, check for failure handling
        mockExists._mock.setReturn(True, logRoot)
        mockAccess._mock.setReturn(False, logRoot, os.W_OK)
        h.ui.resetLogFile(logRoot)
        self.assertEquals(h.ui._log, None)
        h.ui._log = oldLog
        mockExists._mock.assertCalled(logRoot)
        mockMkdir._mock.assertNotCalled()
        mockAccess._mock.assertCalled(logRoot, os.W_OK)

        # reset back to default dir
        logRoot = self.workDir + '/.rbuild'
        h.ui.resetLogFile(logRoot)
        mockExists._mock.assertCalled(logRoot)
        mockMkdir._mock.assertNotCalled()
        mockAccess._mock.assertCalled(logRoot, os.W_OK)

        # reset to not log
        h.ui.resetLogFile(False)
        self.assertEquals(h.ui._log, None)
        mockExists._mock.assertNotCalled()
        mockMkdir._mock.assertNotCalled()
        mockAccess._mock.assertNotCalled()

        # reset to not log again, make sure it doesn't break
        h.ui.resetLogFile(False)
        self.assertEquals(h.ui._log, None)
        mockExists._mock.assertNotCalled()
        mockMkdir._mock.assertNotCalled()
        mockAccess._mock.assertNotCalled()

        # must unmock explicitly due to having mocked with os
        self.unmock()

    def testInput(self):
        h = self.getRbuildHandle(mockOutput=False)
        sys.stdin = StringIO.StringIO()
        sys.stdin.write('input\n')
        sys.stdin.seek(0)
        rc, txt = self.captureOutput(h.ui.input, 'foo')
        self.assertEquals(rc, 'input')
        self.assertEquals(txt, 'foo')
        err = self.assertRaises(errors.RbuildError,
                                 self.captureOutput, h.ui.input, 'foo')
        self.assertEquals(str(err), "Ran out of input while reading for 'foo'")

    def testMultiLineInput(self):
        h = self.getRbuildHandle(mockOutput=False)
        sys.stdin = StringIO.StringIO()
        sys.stdin.write('spam\n\nthe eggs\n')
        sys.stdin.seek(0)
        rc, txt = self.captureOutput(h.ui.multiLineInput, 'foo')
        self.assertEquals(rc, 'spam\n\nthe eggs')
        self.assertEquals(txt, 'foo')

        rc, txt = self.captureOutput(h.ui.multiLineInput, 'bar')
        self.assertEquals(rc, '')
        self.assertEquals(txt, 'bar')

    def testInputPassword(self):
        mock.mock(getpass, 'getpass')
        getpass.getpass._mock.setReturn('result', 'foo')
        h = self.getRbuildHandle()
        assert(h.ui.inputPassword('foo') == 'result')

    def testGetYn(self):
        h = self.getRbuildHandle(mockOutput=False)
        mock.mockMethod(h.ui.input)
        h.ui.input._mock.setReturns(['Y', 'y', '', 'N', 'n'],
                                    'prompt (Default: Y): ')
        for i in range(3):
            rc, txt = self.captureOutput(h.ui.getYn, 'prompt', default=True)
            self.assertEquals(rc, True)
        for i in range(2):
            rc, txt = self.captureOutput(h.ui.getYn, 'prompt', default=True)
            self.assertEquals(rc, False)

        h.ui.input._mock.setReturns(['N', 'n', '', 'Y', 'y'],
                                    'prompt (Default: N): ')
        for i in range(3):
            rc, txt = self.captureOutput(h.ui.getYn, 'prompt', default=False)
            self.assertEquals(rc, False)
        for i in range(2):
            rc, txt = self.captureOutput(h.ui.getYn, 'prompt', default=False)
            self.assertEquals(rc, True)

    def testGetResponse(self):
        h = self.getRbuildHandle(mockOutput=False)
        mock.mockMethod(h.ui.input)

        # allow None response
        h.ui.input._mock.setReturns([''], 'prompt: ')
        rc, txt = self.captureOutput(h.ui.getResponse, 'prompt')
        assert(rc is None)
        assert(txt == '')

        # response is required
        h.ui.input._mock.setReturns(['', 'valid'], 'prompt: ')
        rc, txt = self.captureOutput(h.ui.getResponse, 'prompt', required=True)
        assert(rc == 'valid')
        assert(txt == 'Empty response not allowed.\n')

        # validation function
        h.ui.input._mock.setReturns(['invalid', '', 'valid'], 'prompt: ')
        validationFn = lambda x: x == 'valid'
        rc, txt = self.captureOutput(h.ui.getResponse, 'prompt',
                                     validationFn=validationFn)
        assert(rc == 'valid')
        assert(txt == '')

        # validation and required
        h.ui.input._mock.setReturns(['invalid', '', 'valid'], 'prompt: ')
        rc, txt = self.captureOutput(h.ui.getResponse, 'prompt', required=True,
                                     validationFn=validationFn)
        assert(rc == 'valid')
        self.assertEqual('Empty response not allowed.\n', txt)

        # default
        h.ui.input._mock.setReturns([''], 'prompt (Default: default): ')
        rc, txt = self.captureOutput(h.ui.getResponse, 'prompt',
                                     default='default')
        assert(rc == 'default')
        assert(txt == '')

    def testGetPassword(self):
        h = self.getRbuildHandle()
        mock.mock(getpass, 'getpass')
        getpass.getpass._mock.setReturn('result', 'foo: ')
        getpass.getpass._mock.setFailOnMismatch()
        self.assertEquals(h.ui.getPassword('foo'), 'result')

        getpass.getpass._mock.setReturn('result', 'foo (Default: <obscured>): ')
        self.assertEquals(h.ui.getPassword('foo', default='bar'), 'result')
        getpass.getpass._mock.setReturn('', 'foo (Default: <obscured>): ')
        self.assertEquals(h.ui.getPassword('foo', default='result'), 'result')

    def testGetChoice(self):
        h = self.getRbuildHandle()
        prompt = 'prompt'
        choices = ['a', 'b', 'c']
        args = [prompt, choices, 'Choose one:', None, None, None]
        mock.mockMethod(h.ui._getChoiceResponse)
        h.ui._getChoiceResponse._mock.setReturns([0, 4, 3], *args)
        rc, txt = self.captureOutput(h.ui.getChoice, 'prompt', choices)
        self.assertEqual(rc, 2)

    def testGetChoiceDefault(self):
        h = self.getRbuildHandle()
        prompt = 'prompt'
        choices = ['a', 'b', 'c']
        default = 2
        args = [prompt, choices, 'Choose one:', 2, None, 3]
        mock.mockMethod(h.ui._getChoiceResponse)

        # accept the default
        h.ui._getChoiceResponse._mock.setReturn(3, *args)
        rc, txt = self.captureOutput(
            h.ui.getChoice, prompt, choices, default=default)
        self.assertEqual(rc, default)

        # enter something else
        h.ui._getChoiceResponse._mock.setReturn(1, *args)
        rc, txt = self.captureOutput(
            h.ui.getChoice, prompt, choices, default=default)
        self.assertEqual(rc, 0)

    def testGetChoicePaged(self):
        h = self.getRbuildHandle()
        prompt = 'prompt'
        choices = [chr(x) for x in range(65, 91)]
        args = [prompt, choices, 'Choose one:', None, 5, None]
        mock.mockMethod(h.ui._getChoiceResponse)
        h.ui._getChoiceResponse._mock.setReturns(
            [0, 27, 3], *args)
        rc, txt = self.captureOutput(
            h.ui.getChoice, prompt, choices, pageSize=5)
        self.assertEqual(rc, 2)

    def testGetChoices(self):
        h = self.getRbuildHandle()
        choices = ['a', 'b', 'c']
        mock.mockMethod(h.ui._getChoiceResponse)
        h.ui._getChoiceResponse._mock.setReturn(
            [3], 'prompt', choices, 'Choose:', None, None, [3])
        h.ui._getChoiceResponse._mock.setReturns(
            [0, 4, 3], 'prompt', choices, 'Choose:', None, None, [])
        rc, txt = self.captureOutput(h.ui.getChoices, 'prompt', choices)
        self.assertEqual(rc, [2])

    def testGetChoicesDefault(self):
        h = self.getRbuildHandle()
        choices = ['a', 'b', 'c']
        default = [1, 2]
        mock.mockMethod(h.ui._getChoiceResponse)

        # accept the defaults
        h.ui._getChoiceResponse._mock.setReturn(
            [2, 3], 'prompt', choices, 'Choose:', default, None, [2, 3])
        rc, txt = self.captureOutput(
            h.ui.getChoices, 'prompt', choices, default=default)
        self.assertEqual(rc, [1, 2])

        # add a choice to defaults
        h.ui._getChoiceResponse._mock.setReturn(
            1, 'prompt', choices, 'Choose:', default, None, [2, 3])
        h.ui._getChoiceResponse._mock.setReturn(
            [1, 2, 3], 'prompt', choices, 'Choose:', default, None, [1, 2, 3])
        rc, txt = self.captureOutput(
            h.ui.getChoices, 'prompt', choices, default=default)
        self.assertEqual(rc, [0, 1, 2])

        # remove one of the defaults
        h.ui._getChoiceResponse._mock.setReturn(
            3, 'prompt', choices, 'Choose:', default, None, [2, 3])
        h.ui._getChoiceResponse._mock.setReturn(
            [2], 'prompt', choices, 'Choose:', default, None, [2])
        rc, txt = self.captureOutput(
            h.ui.getChoices, 'prompt', choices, default=default)
        self.assertEqual(rc, [1])

        # toggle a default option
        h.ui._getChoiceResponse._mock.setReturn(
            2, 'prompt', choices, 'Choose:', default, None, [3])
        h.ui._getChoiceResponse._mock.setReturns(
            [2, [2, 3]], 'prompt', choices, 'Choose:', default, None, [2, 3])
        rc, txt = self.captureOutput(
            h.ui.getChoices, 'prompt', choices, default=default)
        self.assertEqual(rc, [1, 2])

        # toggler a non-default options
        h.ui._getChoiceResponse._mock.setReturn(
            1, 'prompt', choices, 'Choose:', default, None, [1, 2, 3])
        h.ui._getChoiceResponse._mock.setReturns(
            [1, [2, 3]], 'prompt', choices, 'Choose:', default, None, [2, 3])
        rc, txt = self.captureOutput(
            h.ui.getChoices, 'prompt', choices, default=default)
        self.assertEqual(rc, [1, 2])

    def testGetChoicesPaged(self):
        h = self.getRbuildHandle()
        choices = [chr(x) for x in range(65, 91)]
        mock.mockMethod(h.ui._getChoiceResponse)
        h.ui._getChoiceResponse._mock.setReturn(
            [3], 'prompt', choices, 'Choose:', None, 5, [3])
        h.ui._getChoiceResponse._mock.setReturns(
            [0, 27, 3], 'prompt', choices, 'Choose:', None, 5, [])
        rc, txt = self.captureOutput(
            h.ui.getChoices, 'prompt', choices, pageSize=5)
        self.assertEqual(rc, [2])

    def test_getChoiceResponsePagination(self):
        h = self.getRbuildHandle()
        choices = [chr(x) for x in range(65, 91)]

        mock.mockMethod(h.ui.getResponse)
        h.ui.getResponse._mock.setReturns(
            ['<', '>', '>', '>', '>', '>', '3'],
            'prompt [1-26]',
            default=None,
            )
        rc, txt = self.captureOutput(
            h.ui._getChoiceResponse, 'prompt', choices, pageSize=7,
            default=None, promptDefault=None, prePrompt='Choose one:')
        self.assertEqual(rc, 3)
        self.assertEqual(
                ''.join(x[0][0] for x in  h.ui.outStream.write._mock.calls),
                '''\
Choose one:
  1. A
  2. B
  3. C
  4. D
  5. E
  6. F
  7. G
  >  (next page)
Choose one:
  1. A
  2. B
  3. C
  4. D
  5. E
  6. F
  7. G
  >  (next page)
Choose one:
  8. H
  9. I
 10. J
 11. K
 12. L
 13. M
 14. N
  <  (previous page)
  >  (next page)
Choose one:
 15. O
 16. P
 17. Q
 18. R
 19. S
 20. T
 21. U
  <  (previous page)
  >  (next page)
Choose one:
 22. V
 23. W
 24. X
 25. Y
 26. Z
  <  (previous page)
Choose one:
 22. V
 23. W
 24. X
 25. Y
 26. Z
  <  (previous page)
Choose one:
 22. V
 23. W
 24. X
 25. Y
 26. Z
  <  (previous page)
''')
