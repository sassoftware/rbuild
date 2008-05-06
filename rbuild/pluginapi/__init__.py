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
# Note that if rmake.lib.pluginlib diverges, we may have to
# override or include a replacement here in order to maintain
# backward compatibility within major versions of rBuild.
from rmake.lib import pluginlib

class Plugin(pluginlib.Plugin):
    """
    Base plugin class for all rbuild plugins.
    """
    def __init__(self, *args, **kw):
        pluginlib.Plugin.__init__(self, *args, **kw)

    def registerCommands(self, handle):
        """
        Use this method to register command line arguments.
        Example::
            def registerCommands(self, handle):
                handle.registerCommand(MyCommandClass)
        """
        pass

    def initialize(self, handle):
        """
        Command called to initialize plugins.  Called after registerCommands.
        All generic plugin initialization should happen here.
        """
        pass
