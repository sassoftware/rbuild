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


from testutils import mock

import errno
import sys

from rbuild_test import rbuildhelp

from rbuild.internal import main
from rbuild import handle
from rbuild import errors
from rbuild import rbuildcfg

from rmake import errors as rmakeerrors
from robj import errors as robjerrors


class MainTest(rbuildhelp.RbuildHelper):

    def testExceptions(self):

        def genRaiseExceptionFn(exception):
            def fn(*args, **kw):
                raise exception
            return fn

        def _testException(exception, debugAll=False):
            self.mock(main.RbuildMain, 'getCommand',
                      genRaiseExceptionFn(exception))
            if debugAll:
                return self.captureOutput(main.main,
                                          ['rbuild', 'help', '--debug-all'])
            return self.captureOutput(main.main,
                                      ['rbuild', 'help'])

        # if rMake isn't running, we get rmake.errors.OpenError
        self.logFilter.add()
        rc, _ = _testException(rmakeerrors.OpenError('Error communicating to server at unix:///var/lib/rmake/socket: Connection refused'))
        self.assertEquals(self.logFilter.records, ['error: Error communicating to server at unix:///var/lib/rmake/socket: Connection refused\n\nCould not contact the rMake server.  Perhaps the rMake service is not\nrunning.  To start the rMake service, as root, try running the command:\nservice rmake restart'])
        self.logFilter.clear()

        # other rmake errors are displayed verbatim, as they are designed for
        self.logFilter.add()
        rc, _ = _testException(rmakeerrors.RmakeError('Dazed and Confused'))
        self.assertEquals(self.logFilter.records, ['error: Dazed and Confused'])
        self.logFilter.clear()

        # robj errors related to authorization and authentication
        self.logFilter.add()
        rc, _ = _testException(robjerrors.HTTPDeleteError(uri='uri', status='status', reason='reason', request='request', response='respone'))
        self.assertEquals(self.logFilter.records, ['error: You are not authorized for this action'])
        self.logFilter.clear()

        self.logFilter.add()
        rc, _ = _testException(robjerrors.HTTPForbiddenError(uri='uri', status='status', reason='reason', request='request', response='respone'))
        self.assertEquals(self.logFilter.records, ['error: You are not authorized for this action'])
        self.logFilter.clear()

        self.logFilter.add()
        rc, _ = _testException(robjerrors.HTTPUnauthorizedError(uri='uri', status='status', reason='reason', request='request', response='respone'))
        self.assertEquals(self.logFilter.records, ['error: There was an error authenticating you with the rbuilder. Check your\nusername and password'])
        self.logFilter.clear()

        # pipe errors generally mean EOF when writing to less, e.g.
        rc, _ = _testException(IOError(errno.EPIPE, 'Pipe Error'))
        self.assertEquals(rc, 0)
        self.assertRaises(IOError, _testException, 
                                IOError('Other IO Error'))
        self.assertRaises(RuntimeError, _testException, 
                          RuntimeError('Other IO Error'))
        self.logFilter.add()
        rc, _ = _testException(errors.RbuildError('foo'))
        self.assertEquals(self.logFilter.records, ['error: foo'])
        self.assertEquals(rc, 1)
        self.logFilter.remove()

        # test with --debug-all
        rc, _ = _testException(errors.RbuildError('foo'))
        self.assertEquals(rc, 1)
        self.assertRaises(errors.RbuildError, _testException,
                          errors.RbuildError('foo'), debugAll=True)

        self.mock(main.RbuildMain, 'main', lambda *args, **kw: None)
        assert(main.main(['rbuild', 'help']) == 0)
        self.mock(main.RbuildMain, 'main', lambda *args, **kw: 23)
        assert(main.main(['rbuild', 'help']) == 23)
        oldargv = sys.argv
        try:
            sys.argv = ['rbuild', 'help']
            assert(main.main() == 23)
        finally:
            sys.argv = oldargv




    def testGetCommand(self):
        mainHandler = main.RbuildMain()
        cmd = mainHandler.getCommand(['rbuild', 'build'], self.rbuildCfg)
        self.assertEquals(cmd.__class__.__name__, 'BuildCommand')

    def testRunCommand(self):
        mainHandler = main.RbuildMain()

        cmd = mainHandler.getCommand(['rbuild', 'help'], self.rbuildCfg)
        productStore = mock.MockObject()
        h = mainHandler.handle
        h.productStore = productStore

        cfg = h.getConfig()
        mock.mock(h.Config, 'isComplete')
        h.Config.isComplete._mock.setReturn(False, cfg)
        mock.mockMethod(h.Config.initializeConfig)
        outputList = []
        rc, txt = self.captureOutput(mainHandler.runCommand,
            cmd, self.rbuildCfg, {}, ['rbuild', 'help'])
        h.Config.initializeConfig._mock.assertNotCalled()

        cmd = mainHandler.getCommand(['rbuild', 'build'], self.rbuildCfg)
        self.rbuildCfg.serverUrl = 'some value'
        productStore = mock.MockObject()
        mainHandler.handle.productStore = productStore
        self.checkCall(mainHandler.runCommand,
                       [cmd, self.rbuildCfg, {'stage' : 'foo'}, [] ],
                       {},
                       'rbuild_plugins.build.BuildCommand.runCommand',
                       [cmd, handle.RbuildHandle, {}, []])
        productStore.setActiveStageName._mock.assertCalled('foo')

        class FakeCommand:
            def runCommand(self, handle, argSet, args):
                raise errors.PluginError('eek')
        cmd = FakeCommand()
        h = mainHandler.handle
        h.ui = mock.MockObject()
        self.assertRaises(errors.PluginError, mainHandler.runCommand, cmd,
            mock.MockObject(), {}, [])
        self.assertEquals(h.ui.popContext._mock.popCall()[0][0],
                          'Command failed with exception %r')
        h.ui.popContext._mock.raiseErrorOnAccess(IOError)
        # Note: not IOError -- the IOError should be ignored and the
        # PluginError should propogate
        self.assertRaises(errors.PluginError, mainHandler.runCommand, cmd,
            mock.MockObject(), {}, [])

    def testUsageByClass(self):
        mainHandler = main.RbuildMain()
        #Test with a regular command
        cmd = mainHandler.getCommand(['rbuild', 'config'], self.rbuildCfg)
        usage = mainHandler._getUsageByClass(cmd)
        self.assertEquals(usage.strip(), 'rbuild config')

        cmd = mainHandler.getCommand(['rbuild', 'init'], self.rbuildCfg)
        usage = mainHandler._getUsageByClass(cmd)
        self.assertEquals(usage.strip(), 'rbuild init <project shortname> <version>\n   or: rbuild init <label>')

        class FakeCommand:
            name = 'bar'
            paramHelp = 'some help'
        cmd = FakeCommand()
        usage = mainHandler._getUsageByClass(cmd)
        self.assertEquals(usage, 'rbuild bar some help')

        cmd = mainHandler.getCommand(['rbuild', 'config'], self.rbuildCfg)
        mainHandler.name = None
        self.assertRaises(AssertionError, mainHandler._getUsageByClass, cmd)

    def testInitializeConfig(self):
        mainHandler = main.RbuildMain()
        cmd = mainHandler.getCommand(['rbuild', 'build'], self.rbuildCfg)
        self.rbuildCfg.serverUrl = 'some value'
        productStore = mock.MockObject()
        h = mainHandler.handle
        h.productStore = productStore

        cfg = h.getConfig()
        mock.mock(h.Config, 'isComplete')
        h.Config.isComplete._mock.setReturn(False, cfg)
        mock.mockMethod(h.Config.initializeConfig)
        self.checkCall(mainHandler.runCommand,
                       [cmd, self.rbuildCfg, {'stage' : 'foo'}, [] ],
                       {},
                       'rbuild_plugins.build.BuildCommand.runCommand',
                       [cmd, handle.RbuildHandle, {}, []])





