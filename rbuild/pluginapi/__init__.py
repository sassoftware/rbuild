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
The rBuild Appliance Developer Process Toolkit Plugin API

The C{rbuild.pluginapi} modules provide public interfaces for
interacting with rBuild plugins, and for rBuild plugins to interact
with each other.  These interfaces will be backward-compatible within
major versions of rBuild.

Module functions, classes, and class methods that do not start
with a C{_} character are public.
"""
import inspect
import new

from decorator import decorator

# Note that if rmake.lib.pluginlib diverges, we may have to
# override or include a replacement here in order to maintain
# backward compatibility within major versions of rBuild.
from rmake.lib import pluginlib

from rbuild import errors



class Plugin(pluginlib.Plugin):
    """
    Base plugin class for all rbuild plugins.
    """

    def __init__(self, *args, **kw):
        pluginlib.Plugin.__init__(self, *args, **kw)

        self._prehooks = {}
        self.handle = None
        for methodName in self.__class__.__dict__:
            if methodName[0] == '_' or hasattr(Plugin, methodName):
                continue
            method = getattr(self, methodName)
            if not inspect.ismethod(method):
                continue
            self._prehooks[methodName] = []
            newMethod = _apiWrapper(self, method, self._prehooks[methodName])
            setattr(self, methodName, newMethod)

    def registerCommands(self):
        """
        Use this method to register command line arguments.
        Example::
            def registerCommands(self):
                self.handle.registerCommand(MyCommandClass)
        """
        return

    def setHandle(self, handle):
        self.handle = handle

    def initialize(self):
        """
        Command called to initialize plugins.  Called after registerCommands.
        All generic plugin initialization should happen here.
        """
        return

    def _installPrehook(self, apiName, hookFunction):
        """
            Installs a prehook for a particular method.
            @param apiName: name of the function to install the prehook for
            @param hookFunction: function to call before calling apiName.
            See handle.installPrehook for description of the reuqired
            hookFunction signature.
        """
        try:
            self._prehooks[apiName].append(hookFunction)
        except KeyError:
            raise errors.InternalError('Cannot install prehook:'
                                       ' No such api method %r' % apiName)

    def _getPrehooks(self, apiName):
        """
            @param apiName: name of api method to get prehooks for.
            @return: modifiable list all hooks attached to api method with
            name C{apiName}.
        """
        try:
            return self._prehooks[apiName]
        except KeyError:
            raise errors.InternalError('Cannot get prehooks:'
                                       ' No such api method %r' % apiName)

def _apiWrapper(self, function, prehooks):
    """
        Internal funciton that adds support for calling prehooks before
        calling api methods.
    """
    @decorator
    def wrapper(apiMethod, _, *args, **kw):
        """
            Wrapper method around api calls that calls prehooks.
        """
        for prehook in prehooks:
            rv = prehook(*args, **kw)
            if rv is not None:
                if isinstance(rv, (tuple, list)) and len(rv) == 2:
                    args, kw = rv
                else:
                    raise errors.InternalError(
                        'Invalid return value from prehook %r'
                        ' for function %r' % (prehook,
                                              function.im_func.__name__))
        return apiMethod(*args, **kw)
    newFunction = wrapper(function)
    newMethod = new.instancemethod(newFunction, self, self.__class__)
    return newMethod

