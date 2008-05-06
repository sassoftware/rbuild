#
# Copyright (c) 2006-2008 rPath, Inc.
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
Implements an RbuildConfiguration object, which is similar to
a C{conarycfg} object.
"""
import os

from conary.lib import cfg
from conary.lib.cfgtypes import CfgString, CfgPathList, CfgDict

from rmake.build.buildcfg import CfgUser

#pylint: disable-msg=R0904
# R0904: Too many public methods

class RbuildConfiguration(cfg.ConfigFile):
    """
    This is the base object for rbuild configuration.
    """
    serverUrl            = CfgString
    user                 = CfgUser
    name                 = CfgString
    contact              = CfgString
    pluginDirs           = (CfgPathList, ['/usr/share/rbuild/plugins',
                                          '~/.rbuild/plugins.d'])
    rmakeUrl             = CfgString
    repositoryMap        = CfgDict(CfgString)

    def __init__(self, readConfigFiles=False, ignoreErrors=False, root=''):
        cfg.ConfigFile.__init__(self)
        if hasattr(self, 'setIgnoreErrors'):
            self.setIgnoreErrors(ignoreErrors)
        if readConfigFiles:
            self.readFiles(root=root)

    def readFiles(self, root=''):
        """
        Populate this configuration object with data from all
        standard locations for rbuild configuration files.
        """
        self.read(root + '/etc/rbuildrc', exception=False)
        if os.environ.has_key("HOME"):
            self.read(root + os.environ["HOME"] + "/" + ".rbuildrc",
                      exception=False)
        self.read('rbuildrc', exception=False)
