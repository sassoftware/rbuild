#
# Copyright (c) rPath, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#


"""
The rBuild Appliance Developer Process Toolkit handle object

The C{handle} module provides the core objects used for consuming rBuild
as a Python API.  Instances of C{RbuildHandle} are the handles used as
the core API item by which consumers of the python API call the plugins
that implement rBuild functionality, and by which plugins communicate
with each other.
"""

import rbuild.facade.conaryfacade
import rbuild.facade.rmakefacade
import rbuild.facade.rbuilderfacade
from rbuild import errors
from rbuild import rbuildcfg
from rbuild import ui
from rbuild.internal import pluginloader
from rbuild.internal.internal_types import AttributeHook
from rbuild.productstore import dirstore


class _PluginProxy(dict):
    """
    Proxy for plugin calls via the handle. Stores the plugin instances
    in an internal dictionary, then presents them as attributes.

    Note that while this is currently a superclass to RbuildHandle, it
    could become an attribute of it instead, changing the calling
    convention from handle.Plugin.foo to handle.plugins.Plugin.foo.
    """

    def __getattr__(self, attr):
        if attr.startswith('_'):
            raise AttributeError
        elif attr in self:
            return self[attr]
        else:
            raise errors.MissingPluginError(attr)


class RbuildHandle(_PluginProxy):
    """
    The rBuild Appliance Developer Process Toolkit handle object.
    @param cfg: rBuild Configuration object, or C{None} to read config
    from disk.
    @param pluginManager: a C{PluginManager} object that contains the plugins
    to use with this handle, or C{None} to load the plugins from disk.
    @ivar product: product definition instance
    @type product: C{proddef}
    @ivar productStore: persistent context for interacting with a product
    @type productStore: C{rbuild.productstore.abstract.ProductStore}
    @ivar: userInterface: C{None} to default to standard UI, or any
    other object which implements the UserInterface methods
    @type userInterface: None, ui.UserInterface
    @ivar logRoot: base directory for logging if using default user
    interface: C{None} (default) to search for a checkout from the
    current directory or $HOME, False to not log, or a specifico
    directory name in which to store a file named C{log}.
    Used only if C{userInterface} is C{None}.
    @type logRoot: None, Bool, str
    """

    # Hook the assignment of productStore so that its parent handle
    # is automatically set (to the current instance).
    productStore = AttributeHook('setHandle')

    def __init__(self, cfg=None, pluginManager=None, productStore=None,
                 userInterface=None, logRoot=None):
        super(RbuildHandle, self).__init__()

        self.product = None
        if cfg is None:
            cfg = rbuildcfg.RbuildConfiguration(readConfigFiles=True)


        if pluginManager is None:
            pluginManager = pluginloader.getPlugins([], cfg.pluginDirs)
        self._cfg = cfg
        self._pluginManager = pluginManager
        for plugin in pluginManager.plugins:
            pluginName = plugin.__class__.__name__
            self[pluginName] = plugin
            plugin.setHandle(self)

        # Provide access to facades
        self.facade = _PluginProxy(self._getFacades())

        # Provide the command manager as if it were a plugin
        self['Commands'] = CommandManager()

        if userInterface is not None:
            self.ui = userInterface
        else:
            if logRoot is not False:
                if not logRoot:
                    logRoot = errors._findCheckoutRoot()
                    if logRoot:
                        logRoot += '/.rbuild'
            #pylint: disable-msg=C0103
            # this name is intentional
            self.ui = ui.UserInterface(self._cfg, logRoot=logRoot)

        if productStore is None:
            # default product store is directory-based
            # Note: will still be None for some cases, such as rbuild init
            proddir = dirstore.getDefaultProductDirectory()
            if proddir is not None:
                productStore = dirstore.CheckoutProductStore(None, proddir)
        self.productStore = productStore

        if productStore:
            self.product = productStore.getProduct()

            if hasattr(productStore, 'getRbuildConfigPath'):
                rBuildConfigPath = productStore.getRbuildConfigPath()
                if rBuildConfigPath is not None:
                    self._cfg.read(rBuildConfigPath, exception=False)
            elif hasattr(productStore, 'getRbuildConfigData'):
                RbuildConfigData = productStore.getRbuildConfigData()
                if RbuildConfigData is not None:
                    self._cfg.readObject('INTERNAL', RbuildConfigData)

    def _getFacades(self):
        '''
        Override this method to provide your own versions of these facades.
        '''
        return {
            'conary': rbuild.facade.conaryfacade.ConaryFacade(self),
            'rmake': rbuild.facade.rmakefacade.RmakeFacade(self),
            'rbuilder': rbuild.facade.rbuilderfacade.RbuilderFacade(self),
        }

    def __repr__(self):
        if self.product:
            return '<RbuildHandle at %s, product %s>' % (hex(id(self)),
                self.product.getProductDefinitionLabel())
        else:
            return '<RbuildHandle at %s>' % (hex(id(self)),)

    def getConfig(self):
        """
        @return: RbuildConfiguration object used by this handle object.
        """
        return self._cfg

    def installPrehook(self, apiMethod, hookFunction):
        """
        Installs a hook that will be called before the given apiMethod
        is called.
        @param apiMethod: api call to add the hook to.  This should be
        a reference to the api object accessible from this handle.
        @param hookFunction: a function that will be called before apiMethod.
        The function must take the same parameters as apiMethod.
        It may modify the parameters passed on to the underlying api method,
        although they should also be valid.

        The parameters may be changed by modifying the arguments passed
        into the hook directly, or by returning the arguments to be passed
        to the api method as a list consisting of a list of arguments, and
        a dictionary of keywords.
        """
        pluginName = apiMethod.im_class.__name__
        methodName = apiMethod.im_func.__name__
        try:
            plugin = self[pluginName]
        except KeyError:
            raise errors.MissingPluginError(pluginName)
        # W0212: Access to a protected member _installPrehook.  Since 
        # we're calling into plugin, whose public methods are api calls,
        # we need to do this here.
        #pylint: disable-msg=W0212
        plugin._installPrehook(methodName, hookFunction)

    def installPosthook(self, apiMethod, hookFunction):
        """
        Installs a hook that will be called after the given apiMethod
        is called.
        @param apiMethod: api call to add the hook to.  This should be
        a reference to the api object accessible from this handle.
        @param hookFunction: a function that will be called after apiMethod.
        The function must take the same parameters as apiMethod, except that
        it must take a leading argument of the current return value, and
        must return the new return value.
        It may modify the return value, and may raise an exception,
        though this is generally discouraged.
        """
        pluginName = apiMethod.im_class.__name__
        methodName = apiMethod.im_func.__name__
        try:
            plugin = self[pluginName]
        except KeyError:
            raise errors.MissingPluginError(pluginName)
        # W0212: Access to a protected member _installPosthook.  Since 
        # we're calling into plugin, whose public methods are api calls,
        # we need to do this here.
        #pylint: disable-msg=W0212
        plugin._installPosthook(methodName, hookFunction)

class CommandManager(object):
    """
        Repository for Command objects available for execution from the
        command line.  Accessible as handle.Commands.
    """
    def __init__(self):
        self._commands = {}

    def registerCommand(self, commandClass):
        """
            Registers a command to make it available for the access by other 
            plugins as well as from the command line.
            @param commandClass: subclass of pluginapi.commands.BaseCommand
        """
        for name in commandClass.commands:
            self._commands[name] = commandClass

    def getCommandClass(self, name):
        """
            @param name: command name as specified on the command line
            @return: commandClass that matches the given command line command.
        """
        return self._commands[name]

    def getAllCommandClasses(self):
        """
            @return: all registered command classes
        """
        return set(self._commands.values())
