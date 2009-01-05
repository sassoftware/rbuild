#
# Copyright (c) 2008 rPath, Inc.
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
            eValue.url = eValue.url.__safe_str__()
            try:
                raise eType, eValue, eTraceback
            finally:
                # Circular reference through eTraceback
                del eType, eValue, eTraceback


class ServerProxy(util.ServerProxy):
    """
    Generic ServerProxy that supports injecting username/password into
    a URI without revealing the password in tracebacks or error
    messages.
    """

    #pylint: disable-msg=R0913
    # we really need all those arguments
    def __init__(self, uri, username=None, password=None, *args, **kwargs):
        util.ServerProxy.__init__(self, uri, *args, **kwargs)

        if username is not None:
            password = util.ProtectedString(password)
            self.__host = ProtectedTemplate('${user}:${password}@${host}',
                user=username, password=password, host=self.__host)

    def __repr__(self):
        """
        Return a representation of the server proxy using a clean URI.

        @return: str
        """
        return '<ServerProxy for %s%s>' % (self.__host.__safe_str__(),
            self.__handler)

    def _createMethod(self, name):
        """
        Use our C{_Method} so we can catch and sanitize
        all C{ProtocolError} thrown by the transport.

        @param name: XMLRPC method name
        @return: L{_Method}
        """
        return _Method(self._request, name)
