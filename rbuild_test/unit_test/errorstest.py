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
import os
from rbuild_test import rbuildhelp
import tempfile

from conary.lib import util
from rbuild import errors


class ErrorsTest(rbuildhelp.RbuildHelper):
    def testExceptHook(self):
        _genExcepthook = util.genExcepthook
        cwd = os.getcwd()
        try:
            # Create a non-"checkout" dir
            checkoutDir = tempfile.mkdtemp()
            os.chdir(checkoutDir)

            def assertUsesRoot(error, prefix, *args, **kwargs):
                self.failUnlessEqual(prefix, 'rbuild-error-')
                return lambda a, b, c: None

            # Expect that /tmp is used
            self.mock(os, 'getenv', mock.MockObject())
            os.getenv._mock.setReturn(None, 'HOME')
            util.genExcepthook = assertUsesRoot
            errors.genExcepthook()(None, None, None)

            # Expect that $HOME is used
            homeDir = tempfile.mkdtemp()
            os.mkdir(homeDir + '/.rbuild')
            def assertUsesHome(error, prefix, *args, **kwargs):
                self.failUnlessEqual(prefix, homeDir + '/.rbuild/tracebacks/rbuild-error-')
                return lambda a, b, c: None

            os.getenv._mock.setReturn(homeDir, 'HOME')
            util.genExcepthook = assertUsesHome
            errors.genExcepthook()(None, None, None)
            self.unmock()

            # Turn the non-"checkout" dir into a "checkout", but not writable
            os.mkdir(checkoutDir + '/.rbuild')
            os.chmod(checkoutDir + '/.rbuild', 0555)

            # Expect that /tmp is used
            util.genExcepthook = assertUsesRoot
            errors.genExcepthook()(None, None, None)

            # Make the checkout writable
            os.chmod(checkoutDir + '/.rbuild', 0755)

            def assertUsesCheckout(error, prefix, *args, **kwargs):
                self.failUnlessEqual(prefix, checkoutDir + '/.rbuild/tracebacks/rbuild-error-')
                return lambda a, b, c: None

            # Expect that checkout is used
            util.genExcepthook = assertUsesCheckout
            errors.genExcepthook()(None, None, None)


            # Make the tracebacks dir unwritable
            os.chmod(checkoutDir + '/.rbuild/tracebacks', 0555)

            # Expect that /tmp is used
            util.genExcepthook = assertUsesRoot
            errors.genExcepthook()(None, None, None)

            os.chmod(checkoutDir + '/.rbuild/tracebacks', 0755)
        finally:
            util.genExcepthook = _genExcepthook
            util.rmtree(checkoutDir)
            util.rmtree(homeDir)
            os.chdir(cwd)

    def testExceptions(self):
        # Normal cases
        err = errors.RbuildError('foo')
        self.assertEqual(err.msg, 'foo')
        self.assertEqual(str(err), 'foo')
        self.assertEqual(repr(err), "RbuildError(msg='foo')")

        err = errors.InvalidHookReturnError(hook='foo_hook',
                method='bar_method')
        self.assertEqual(err.hook, 'foo_hook')
        self.assertEqual(err.method, 'bar_method')
        self.assertEqual(str(err), "Invalid return value from prehook "
                "'foo_hook' for function 'bar_method'")
        self.assertEqual(repr(err), "InvalidHookReturnError("
                "hook='foo_hook', method='bar_method')")
        self.assertRaises(AttributeError, lambda: err.foo)

        # Failure cases - positional
        err = self.assertRaises(TypeError, errors.RbuildError, 'foo', 'bar')
        self.assertEqual(err.args[0], 'Exception RbuildError takes exactly 1 '
                'argument (2 given)')

        err = self.assertRaises(TypeError, errors.RbuildError, 'foo',
                msg='foo')
        self.assertEqual(err.args[0], 'Exception RbuildError cannot take '
                'both positional and keyword arguments')

        # Failure cases - keyword
        err = self.assertRaises(TypeError, errors.InvalidHookReturnError,
                hook='foo_hook')
        self.assertEqual(err.args[0], "Expected argument 'method' to "
                "exception InvalidHookReturnError")

        err = self.assertRaises(TypeError, errors.RbuildError, msg='foo',
                bar='bork')
        self.assertEqual(err.args[0], "Exception RbuildError got an "
                "unexpected argument 'bar'")


