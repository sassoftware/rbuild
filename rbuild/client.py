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
The rBuild Appliance Developer Process Toolkit client object

The C{client} module provides the core objects used for consuming rBuild
as a Python API.  Instances of C{rBuildClient} are the handles used as
the core API item by which consumers of the python API call the plugins
that implement rBuild functionality, and by which plugins communicate
with each other.
"""

class rBuildClient(object):
    def __init__(self, pluginMgr, cfg):
        self.cfg = cfg
        self.pluginMgr = pluginMgr
        for plugin in pluginMgr.plugins:
            setattr(self, plugin.__class__.__name__, plugin)

def getClient(disabledPlugins=None):
    cfg = rbuild.rBuildConfiguration(ignoreErrors=True)
    plugins = pluginloader.getPlugins(cfg, disabledPlugins)
    return rbuildClient(cfg, plugins)
