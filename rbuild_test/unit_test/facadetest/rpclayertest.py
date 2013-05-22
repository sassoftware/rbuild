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


'''
Tests for the generic RPC proxy defined in rbuild.facade,
and the error handling and scrubbing it provides.
'''


from rbuild_test import rbuildhelp
import xmlrpclib

from conary.lib import util
from rbuild import facade

class MockTransport(object):
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def request(self, *args, **kwargs):
        if len(args) == 2:
            uri, body = args
            handler = uri.path

            username = uri.userpass[0]
            password = uri.userpass[1]
            host = str(uri.hostport.host.name)

            full_url = str(uri)
        else:
            uri, handler, body = args

            username = uri._substArgs['user']
            password = uri._substArgs['password']
            host = uri._substArgs['host']

            full_url = uri + handler

        verbose = kwargs.get('verbose', 0)

        method = util.xmlrpcLoad(body)[1]

        self.calls.append((username, password, host, handler, method))
        if self.fail:
            raise xmlrpclib.ProtocolError(full_url,
                500, 'Totally Awesome Error', {})
        return ()

    def assertCalled(self, username, password, host, handler, method):
        calls = [(username, password, host, handler, method)]
        if self.calls != calls:
            raise AssertionError("Transport call incorrect: "
                "%r (actual) != %r (expected)" % (calls, self.calls))


class RPCLayerTest(rbuildhelp.RbuildHelper):
    def testProtectedCall(self):
        """
        Ensure that a RPC call generates a protected URI fragment
        so that credentials do not leak.
        """
        transport = MockTransport()
        server = facade.ServerProxy('http://www.example.foo/',
            username='foo', password='bar', transport=transport)
        server.doStuff()
        transport.assertCalled('foo', 'bar', 'www.example.foo', '/',
            'doStuff')

        if isinstance(server, xmlrpclib.ServerProxy):
            self.failUnlessEqual(repr(server),
            '<ServerProxy for foo:<PASSWORD>@www.example.foo/>')
        else:
            self.failUnlessEqual(repr(server),
             '<ServerProxy for http://foo:<PASSWD>@www.example.foo/>')

    def testNestedCall(self):
        """
        Ensure that a nested RPC call generates a protected URI
        fragment so that credentials do not leak.
        """
        transport = MockTransport()
        server = facade.ServerProxy('http://www.example.foo/',
            username='foo', password='bar', transport=transport)
        server.somemodule.doStuff()
        transport.assertCalled('foo', 'bar', 'www.example.foo', '/',
            'somemodule.doStuff')

    def testFailingCall(self):
        """
        Ensure that ProtocolErrors raised by the transport have
        their URI fragments sanitized.
        """
        transport = MockTransport(fail=True)
        server = facade.ServerProxy('http://www.example.foo/',
            username='foo', password='bar', transport=transport)
        try:
            server.doStuff()
        except xmlrpclib.ProtocolError, e_value:
            self.failUnlessEqual(e_value.errcode, 500)
            self.failUnlessEqual(e_value.errmsg, 'Totally Awesome Error')
        else:
            self.fail("Call did not raise ProtocolError")
        transport.assertCalled('foo', 'bar', 'www.example.foo', '/',
            'doStuff')


