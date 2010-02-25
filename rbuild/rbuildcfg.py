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
from conary.lib.cfgtypes import CfgString, CfgPathList, CfgBool
from conary.conarycfg import CfgRepoMap, CfgFingerPrint, CfgFingerPrintMap

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
    rmakeUser            = CfgUser
    rmakeUrl             = CfgString
    rmakePluginDirs      = (CfgPathList, ['/usr/share/rmake/plugins',
                                          '~/.rmake/plugins.d'])
    repositoryMap        = CfgRepoMap
    quiet                = (CfgBool, False)
    signatureKey         = CfgFingerPrint
    signatureKeyMap      = CfgFingerPrintMap


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
        @param root: if specified, search for config file under the given
        root instead of on the base system.  Useful for testing.
        """
        self.read(root + '/etc/rbuildrc', exception=False)
        if os.environ.has_key("HOME"):
            self.read(root + os.environ["HOME"] + "/" + ".rbuildrc",
                      exception=False)
        self.read('rbuildrc', exception=False)

    def writeCheckoutFile(self, path):
        """
        Write portions of the configuration to a file at C{path}. Most
        options will only appear as comments showing the default value
        and the value at the time this function was called. Some
        options will have their actual values set, and others will not
        appear at all.
        @param path: name of file to write (absolute or relative path)
        @type path: string
        """
        out = open(path, 'w')
        options = dict(prettyPrint=True)

        omitItems = ['user', 'rmakeUser']
        setItems = ['repositoryMap']

        def _formatItem(theItem, theValue):
            return ', '.join(theItem.valueType.toStrings(theValue, options))

        for key, item in sorted(self._options.items()):
            if key in omitItems:
                # Omit these entirely
                continue

            value = self[key]
            if key in setItems:
                # Write values for these
                out.write("# %s (Default: %s)\n" % (item.name,
                    _formatItem(item, item.default)))
                self._writeKey(out, item, value, options)
            else:
                # Write docs for these (the normal case)
                out.write("# %s (Default: %s) (At `rbuild init': %s)\n" % (
                    item.name,
                    _formatItem(item, item.default), _formatItem(item, value)))
