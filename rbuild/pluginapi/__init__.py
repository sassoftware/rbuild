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
The rBuild Appliance Developer Process Toolkit Plugin API

The C{rbuild.pluginapi} modules provide public interfaces for
interacting with rBuild plugins, and for rBuild plugins to interact
with each other.  These interfaces will be backward-compatible within
major versions of rBuild.

Module functions, classes, and class methods that do not start
with a C{_} character are public.
"""
import functools
import inspect
import new
import os
from conary.lib import cfg


# Note that if rmake.lib.pluginlib diverges, we may have to
# override or include a replacement here in order to maintain
# backward compatibility within major versions of rBuild.
from rmake.lib import pluginlib

from rbuild import errors
from rbuild import handle
from rbuild.internal.internal_types import WeakReference

class PluginConfiguration(cfg.ConfigSection):
    """Base plugin configuration class"""

    def __init__(self, *args, **kwargs):
        self._empty = True
        super(PluginConfiguration, self).__init__(*args, **kwargs)

    def addConfigOption(self, *args, **kwargs):
        self._empty = False
        ret = super(PluginConfiguration, self).addConfigOption(*args, **kwargs)
        return ret

class Plugin(pluginlib.Plugin):
    """
    Base plugin class for all rbuild plugins.
    """
    #pylint: disable-msg=R0201
    # "Method could be a function" but this is a base class

    # The parent handle should be a weak reference to avoid a loop;
    # this descriptor will transparently handle the dereferenceing.
    handle = WeakReference()

    # Default plugin configuration
    PluginConfiguration = PluginConfiguration

    def __init__(self, *args, **kw):
        pluginlib.Plugin.__init__(self, *args, **kw)
        self.pluginCfg = None

        self._prehooks = {}
        self._posthooks = {}
        for methodName in self.__class__.__dict__:
            if methodName[0] == '_' or hasattr(Plugin, methodName):
                continue
            method = getattr(self, methodName)
            if not inspect.ismethod(method):
                continue
            self._prehooks[methodName] = []
            self._posthooks[methodName] = []
            newMethod = _apiWrapper(method,
                self._prehooks[methodName],
                self._posthooks[methodName])
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

    def registerFacade(self, handle):
        """
        Use this method to modify the set of available facades. Called
        before initialize.
        """

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
        See handle.installPrehook for description of the required
        hookFunction signature.
        """
        try:
            self._prehooks[apiName].append(hookFunction)
        except KeyError:
            raise errors.InvalidAPIMethodError(apiName)

    def _getPrehooks(self, apiName):
        """
        @param apiName: name of api method to get prehooks for.
        @return: modifiable list all prehooks attached to api method with
        name C{apiName}.
        """
        try:
            return self._prehooks[apiName]
        except KeyError:
            raise errors.InvalidAPIMethodError(apiName)

    def _installPosthook(self, apiName, hookFunction):
        """
        Installs a posthook for a particular method.
        @param apiName: name of the function to install the posthook for
        @param hookFunction: function to call before calling apiName.
        See handle.installPosthook for description of the required
        hookFunction signature.
        """
        try:
            self._posthooks[apiName].append(hookFunction)
        except KeyError:
            raise errors.InvalidAPIMethodError(apiName)

    def _getPosthooks(self, apiName):
        """
        @param apiName: name of api method to get posthooks for.
        @return: modifiable list all posthooks attached to api method with
        name C{apiName}.
        """
        try:
            return self._posthooks[apiName]
        except KeyError:
            raise errors.InvalidAPIMethodError(apiName)

def _apiWrapper(method, prehooks, posthooks):
    """
    Internal function that adds support for calling pre- and post-hooks
    before calling api methods.
    @param function: actual function to wrap
    @param prehooks: functions to call before calling actual function
    @param posthooks: functions to call after calling actual function
    """
    func = method.im_func
    self = method.im_self
    def wrapper(xself, *args, **kw):
        #pylint: disable-msg=C0999
        # internal wrapper function that merely preserves signature
        """
        Wrapper method around api calls that calls pre/post hooks.
        """
        for prehook in prehooks:
            rv = prehook(*args, **kw)
            if rv is not None:
                if isinstance(rv, (tuple, list)) and len(rv) == 2:
                    args, kw = rv
                else:
                    raise errors.InvalidHookReturnError(hook=prehook,
                            method=method.__name__)
        rv = method(*args, **kw)
        for posthook in posthooks:
            rv = posthook(rv, *args, **kw)
        return rv
    wrapper.__name__ = method.__name__
    wrapper.__doc__ = method.__doc__
    wrapped = new.instancemethod(wrapper, self, self.__class__)
    return wrapped

