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
The rBuild Appliance Developer Process Toolkit Facades

The C{rbuild.facade} modules provide public facades for lower-level
rPath APIs.  These facades are intended to be APIs that are:
 - High-level: do not require many lines of boilerplate to accomplish
   an action.
 - Very stable: when underlying APIs are modified, only the facade
   should need to be adapted, not the plugins that use the facade.

These APIs will be backward-compatible within major versions of rBuild.

Module functions, classes, and class methods that do not start
with a C{_} character are public.
"""

import sys
import urllib
import xmlrpclib
from conary.lib import util


class ProtectedTemplate(util.ProtectedTemplate):
    """
    Extension of L{conary.lib.util.ProtectedTemplate} that supports
    appending fixed strings to the template. The transport handler
    will (unknowingly) use this when it throws C{ProtocolError}.
    """
    #pylint: disable-msg=R0904
    # * lots of methods inherited from a builtin type

    def __add__(self, other):
        """
        Append string C{other} to the template.

        @param other: String to add to template
        @type  other: str
        @return: L{ProtectedTemplate}
        """
        #pylint: disable-msg=E1101
        # * parameters added in __new__ aren't lint-friendly
        assert isinstance(other, str)
        template = self._templ.template + other
        return ProtectedTemplate(template, **self._substArgs)


class _Method(xmlrpclib._Method):
    """
    Extension of L{xmlrpclib._Method} that sanitizes any
    C{ProtocolError}s thrown in a call, using C{__safe_str__}().
    """

    def __getattr__(self, name):
        """
        Handle nested calls (e.g. C{proxy.foo.bar()}) while still
        returning our own C{_Method}. Note that unlike the python
        version, this will work with subclasses too.

        @param name: Name of sub-method to generate
        @return: L{_Method}
        """
        return self.__class__(self.__send, "%s.%s" % (self.__name, name))

    def __call__(self, *args):
        """
        Catch C{ProtocolError} thrown by the transport and sanitize
        the C{url} parameter.

        @param args: Arguments to marshal over XMLRPC
        @return: Result of RPC
        """
        try:
            return xmlrpclib._Method.__call__(self, *args)
        except xmlrpclib.ProtocolError:
            eType, eValue, eTraceback = sys.exc_info()
            # eValue.url = eValue.url.__safe_str__()
            try:
                raise eType, eValue, eTraceback
            finally:
                # Circular reference through eTraceback
                del eType, eValue, eTraceback


class ServerProxy(xmlrpclib.ServerProxy):
    """
    Generic ServerProxy that supports injecting username/password into
    a URI without revealing the password in tracebacks or error
    messages.
    """

    # This is a modified copy of the ServerProxy from conary.lib.util in
    # conary 2.2.x. It was coppied for compatibility with conary 2.3 which
    # changed the conary server proxy to not be based on ServerProxy from
    # xmlrpclib.

    #pylint: disable-msg=R0913
    # we really need all those arguments
    def __init__(self, uri, username=None, password=None, *args, **kwargs):
        xmlrpclib.ServerProxy.__init__(self, uri, *args, **kwargs)
        # Hide password
        userpass, hostport = urllib.splituser(self.__host)
        if userpass and not username:
            self.__host = hostport
            username, password = urllib.splitpasswd(userpass)

        if username:
            password = util.ProtectedString(urllib.quote(password))
            self.__host = ProtectedTemplate('${user}:${password}@${host}',
                user=username, password=password, host=self.__host)

    def __repr__(self):
        """
        Return a representation of the server proxy using a clean URI.

        @return: str
        """

        return "<ServerProxy for %s%s>" % (repr(self.__host), self.__handler)

    __str__ = __repr__

    def _createMethod(self, name):
        """
        Use our C{_Method} so we can catch and sanitize
        all C{ProtocolError} thrown by the transport.

        @param name: XMLRPC method name
        @return: L{_Method}
        """

        return _Method(self._request, name)

    def _request(self, methodname, params):
        # Call a method on the remote server
        request = util.xmlrpcDump(params, methodname,
            encoding = self.__encoding, allow_none=self.__allow_none)

        response = self.__transport.request(
            self.__host,
            self.__handler,
            request,
            verbose=self.__verbose)

        if len(response) == 1:
            response = response[0]

        return response

    def __getattr__(self, name):
        # magic method dispatcher
        if name.startswith('__'):
            raise AttributeError(name)
        #from conary.lib import log
        #log.debug('Calling %s:%s' % (self.__host.split('@')[-1], name)
        return self._createMethod(name)
