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
The rBuild Appliance Developer Process Toolkit handle object

The C{handle} module provides the core objects used for consuming rBuild
as a Python API.  Instances of C{RbuildHandle} are the handles used as
the core API item by which consumers of the python API call the plugins
that implement rBuild functionality, and by which plugins communicate
with each other.
"""
from conary.lib import log

from rbuild import errors
from rbuild import rbuildcfg
from rbuild.internal import pluginloader
import rbuild.facade.conaryfacade
import rbuild.facade.rmakefacade
import rbuild.facade.rbuilderfacade

class _Facade(object):
    """
    Private internal container for facades provided via the handle
    """

class RbuildHandle(object):
    """
    The rBuild Appliance Developer Process Toolkit handle object.
    @param cfg: rBuild Configuration object, or C{None} to read config
    from disk.
    @param pluginManager: a C{PluginManager} object that contains the plugins
    to use with this handle, or C{None} to load the plugins from disk.
    """
    def __init__(self, cfg=None, pluginManager=None, productStore=None):
        if cfg is None:
            cfg = rbuildcfg.RbuildConfiguration(readConfigFiles=True)


        if pluginManager is None:
            pluginManager = pluginloader.getPlugins([], cfg.pluginDirs)
        self._cfg = cfg
        self._pluginManager = pluginManager
        for plugin in pluginManager.plugins:
            setattr(self, plugin.__class__.__name__, plugin)
            plugin.setHandle(self)
        # Provide access to facades
        self.facade = _Facade()
        self.facade.conary = rbuild.facade.conaryfacade.ConaryFacade(self)
        self.facade.rmake = rbuild.facade.rmakefacade.RmakeFacade(self)
        self.facade.rbuilder = rbuild.facade.rbuilderfacade.RbuilderFacade(self)
        # C0103: bad variable name.  We want this variable to match the
        # convention of variables accessible from the handle.  Like a plugin,
        # which is available under its class name, the commands are available
        # under handle.Commands.
        # pylint: disable-msg=C0103
        self.Commands = CommandManager()

        if productStore is None:
            # E1101: Instance of 'RbuildHandle' has no 'Product' member
            # Product is a required builtin plugin.
            # pylint: disable-msg=E1101
            if hasattr(self, 'Product'):
                productStore = self.Product.getDefaultProductStore()
            else:
                log.warning('Product plugin not loaded - check'
                            ' pluginDirs setting')
                productStore = None
        self._productStore = productStore
        if productStore is not None:
            self._cfg.read(productStore.getRbuildConfigPath(), exception=False)

    def getConfig(self):
        """
        @return: RbuildConfiguration object used by this handle object.
        """
        return self._cfg

    def getProductStore(self):
        return self._productStore

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
            plugin = getattr(self, pluginName)
        except AttributeError:
            raise errors.InternalError(
                    'Could not install hook %r:'
                    ' No such plugin %r' % (hookFunction.__name__, pluginName))
        # W0212: Access to a protected member _installPrehook.  Since 
        # we're calling into plugin, whose public methods are api calls,
        # we need to do this here.
        #pylint: disable-msg=W0212
        plugin._installPrehook(methodName, hookFunction)

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

