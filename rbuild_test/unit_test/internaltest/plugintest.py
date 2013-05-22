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



from rbuild_test import rbuildhelp

from rbuild import errors
from rbuild import pluginapi

class MyPlugin(pluginapi.Plugin):
    foo = 'bar'

    def myApiCall(self, *args, **kw):
        print 'api call: %s, %s' % (args, kw)
        return 'return value'

class PluginTest(rbuildhelp.RbuildHelper):

    def myHook(self, *args, **kw):
        args = ('foo', ) + args[1:]
        return args, {'newkw' : kw['kw']}

    def myHook2(self, *args, **kw): 
        args = ('barz ' + args[0], ) + args[1:]
        return args, {'newkw2' : kw['newkw']}

    def myPostHook(self, rv, *args, **kw): 
        return rv+' augmented'

    def myPostHookError(self, rv, *args, **kw): 
        raise KeyError

    def brokenHook(self, *args, **kw):
        return 3

    def testPrehooks(self):
        plugin = MyPlugin('plugin', 'path', None)
        rc, txt = self.captureOutput(plugin.myApiCall, 'arg1', kw='kw1')
        assert(rc == 'return value')
        self.assertEquals(txt, "api call: ('arg1',), {'kw': 'kw1'}\n")
        plugin._installPrehook('myApiCall', self.myHook)
        rc, txt = self.captureOutput(plugin.myApiCall, 'arg1', kw='kw1')
        assert(rc == 'return value')
        self.assertEquals(txt, "api call: ('foo',), {'newkw': 'kw1'}\n")
        plugin._installPrehook('myApiCall', self.myHook2)
        rc, txt = self.captureOutput(plugin.myApiCall, 'arg1', kw='kw1')
        self.assertEquals(txt, "api call: ('barz foo',), {'newkw2': 'kw1'}\n")
        plugin._installPrehook('myApiCall', self.brokenHook)
        err = self.discardOutput(
                self.assertRaises, errors.InvalidHookReturnError, 
                plugin.myApiCall, 'arg1', kw='kw1')
        self.assertEquals(err.hook, self.brokenHook)
        # after removing the broken hook this should work.
        plugin._getPrehooks('myApiCall').remove(self.brokenHook)
        rc, txt = self.captureOutput(plugin.myApiCall, 'arg1', kw='kw1')

    def testPrehookErrors(self):
        plugin = MyPlugin('plugin', 'path', None)

        err = self.assertRaises(errors.InvalidAPIMethodError,
                plugin._installPrehook, 'nosuchApi', self.myHook)
        self.assertEquals(err.method, 'nosuchApi')

        err = self.assertRaises(errors.InvalidAPIMethodError,
                plugin._getPrehooks, 'nosuchApi')
        self.assertEquals(err.method, 'nosuchApi')

    def testPosthooks(self):
        plugin = MyPlugin('plugin', 'path', None)
        plugin._installPosthook('myApiCall', self.myPostHook)
        rc, txt = self.captureOutput(plugin.myApiCall, 'arg1', kw='kw1')
        assert(rc == 'return value augmented')

    def testPosthookErrors(self):
        plugin = MyPlugin('plugin', 'path', None)
        plugin._installPosthook('myApiCall', self.myPostHookError)
        err = self.discardOutput(
                self.assertRaises, KeyError, 
                plugin.myApiCall, 'arg1', kw='kw1')
        # after removing the broken hook this should work.
        plugin._getPosthooks('myApiCall').remove(self.myPostHookError)
        rc, txt = self.captureOutput(plugin.myApiCall, 'arg1', kw='kw1')
        assert(rc == 'return value')

        err = self.assertRaises(errors.InvalidAPIMethodError,
                plugin._installPosthook, 'nosuchApi', self.myPostHook)
        self.assertEquals(err.method, 'nosuchApi')
        err = self.assertRaises(errors.InvalidAPIMethodError,
                plugin._getPosthooks, 'nosuchApi')
        self.assertEquals(err.method, 'nosuchApi')


