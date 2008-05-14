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
Conary facade module

This module provides a high-level stable API for use within rbuild
plugins.  It provides public methods which are only to be accessed
via C{handle.facade.conary} which is automatically available to
all plugins through the C{handle} object.
"""

import copy

from conary import conarycfg
from conary import conaryclient
from conary import checkin
from conary.deps import deps
from conary import updatecmd
from conary import versions


class ConaryFacade(object):
    """
    The rBuild Appliance Developer Process Toolkit Conary facade.

    Note that the contents of objects marked as B{opaque} may vary
    according to the version of Conary in use, and the contents
    of such objects are not included in the stable rBuild API.
    """
    def __init__(self, handle):
        """
        @param handle: The handle with which this instance is associated.
        """
        self._handle = handle
        self._conaryCfg = None

#{ Private Methods
    def _parseRBuilderConfigFile(self, cfg):
        """
        Include conary configuration file provided by rBuilder
        """
        serverUrl = self._handle.getConfig().serverUrl
        if serverUrl:
            cfg.includeConfigFile(serverUrl + '/conaryrc')

    def _getConaryClient(self):
        """
        Get a conaryclient object
        """
        return conaryclient.ConaryClient(self.getConaryConfig())

    def _getRepositoryClient(self):
        """
        Get a repository object from a conaryclient
        """
        return self._getConaryClient().getRepos()

    @staticmethod
    def _getVersion(version):
        """
        Converts a version string into an B{opaque} Conary version object,
        or returns the B{opaque} version object.
        @param version: a representation of a conary version
        @type version: string or B{opaque} conary.versions.Version
        @return: B{opaque} Conary version object
        @rtype: conary.versions.Version
        """
        if type(version) is str:
            return versions.VersionFromString(version)
        return version

    @staticmethod
    def _getLabel(label):
        """
        Converts a label string into an B{opaque} Conary label object,
        or returns the B{opaque} label object.
        @param label: a representation of a conary label
        @type label: string or B{opaque} conary.versions.Label
        @return: B{opaque} Conary label object
        @rtype: conary.versions.Label
        """
        if type(label) is str:
            return versions.Label(label)
        return label

    @staticmethod
    def _getFlavor(flavor=None):
        """
        Converts a version string into an B{opaque} Conary flavor object
        or returns the B{opaque} flavor object.
        @param flavor: conary flavor
        @type flavor: string or B{opaque} conary.deps.deps.Flavor
        @return: B{opaque} Conary flavor object
        @rtype: conary.deps.deps.Flavor
        """
        if flavor is None:
            return(deps.Flavor())
        if type(flavor) is str:
            return deps.parseFlavor(flavor)
        return flavor

    def _findTrove(self, name, version, flavor=None, labelPath=None):
        """
        Gets a reference to a trove in the repository.
        @param name: package to find
        @type name: string
        @param version: version of package to find
        @type version: string or C{conary.versions.Version} B{opaque}
        @param flavor: flavor of package to find (optional)
        @type flavor: string or C{deps.Flavor} B{opaque}
        @param labelPath: label(s) to find package on
        @type labelPath: None, conary.versions.Label, or list of conary.versions.Label
        @return: C{(name, version, flavor)} tuple.
        Note that C{version} and C{flavor} objects are B{opaque}.
        @rtype: (string, conary.versions.Version conary.deps.deps.Flavor)
        """
        repos = self._getRepositoryClient()
        flavor = self._getFlavor(flavor)
        troveTup, = repos.findTrove(labelPath, (name, version, flavor))
        return troveTup

    @staticmethod
    def _versionToString(version):
        """
        Takes either a string or an B{opaque} C{version.Version}
        object and returns a string.  The inverse of C{_getVersion}
        @param version: trove version
        @type version: string or B{opaque} C{conary.versions.Version}
        @return: version
        @rtype: string
        """
        if type(version) is versions.Version:
            version = version.asString()
        return version

    @staticmethod
    def _flavorToString(flavor):
        """
        Takes either a string or an B{opaque} C{conary.deps.deps.Flavor}
        object and returns a string.  The inverse of C{_getFlavor}
        @param flavor: trove flavor
        @type flavor: None, string, or B{opaque} C{conary.deps.deps.Flavor}
        @return: flavor
        @rtype: string
        """
        if flavor is None:
            return ''
        if type(flavor) is deps.Flavor:
            flavor = str(flavor)
        return flavor

    @classmethod
    def _troveTupToStrings(cls, name, version, flavor=None):
        """
        Turns a (name, version, flavor) tuple with strings or objects
        as elements, and converts it to a (name, version, flavor)
        tuple with only strings, to avoid unnecessarily exporting
        conary objects into the rbuild API.
        @param name: trove name
        @type name: string
        @param version: trove version
        @type version: string or B{opaque} C{conary.versions.Version}
        @param flavor: trove flavor
        @type flavor: None, string, or B{opaque} C{conary.deps.deps.Flavor}
        @return: (name, version, flavor) tuple
        @rtype: (string, string, string)
        """
        version = cls._versionToString(version)
        flavor = cls._flavorToString(version)
        return (name, version, flavor)
#}


    def getConaryConfig(self):
        """
        Fetches a (possibly cached) B{opaque} conary config object with all
        appropriate data inherited from the associated rbuild config
        object.
        @return: C{conarycfg.ConaryConfiguration} B{opaque} object
        """
        if not self._conaryCfg:
            cfg = conarycfg.ConaryConfiguration(False)
            rbuildCfg = self._handle.getConfig()
            self._parseRBuilderConfigFile(cfg)
            cfg.repositoryMap.update(rbuildCfg.repositoryMap)
            cfg.user.append(('*',) + rbuildCfg.user)
            cfg.name = rbuildCfg.name
            cfg.contact = rbuildCfg.contact
            self._conaryCfg = cfg
        return self._conaryCfg

    def checkout(self, package, label, targetDir=None):
        """
        Create a subdirectory containing a checkout of a conary
        source package.  Similar to the C{cvc checkout} command.
        @param package: name of package
        @type package: string
        @param label: label to find package on
        @type label: string
        @param targetDir: subdirectory into which to check out the package,
        defaults to C{package}
        @type targetDir: string
        """
        cfg = self.getConaryConfig()
        # FIXME: remove this problematic workaround when CNY-2783 fixed
        cfg.buildLabel = label
        checkin.checkout(self._getRepositoryClient(), cfg,
                         targetDir, ['%s=%s' % (package, label)])

    def updateCheckout(self, targetDir):
        """
        Create a subdirectory containing a checkout of a conary
        source package.  Similar to the C{cvc update} command.
        @param targetDir: subdirectory containing package to update
        @type targetDir: string
        """
        checkin.updateSrc(self._getRepositoryClient(), [targetDir])

    def createNewPackage(self, package, label):
        """
        Create a subdirectory containing files to initialize a new
        conary source package.  Similar to the C{cvc newpkg} command.
        @param package: name of package
        @type package: string
        @param label: label to create package on
        @type label: string
        """
        checkin.newTrove(self._getRepositoryClient(), self.getConaryConfig(),
                         '%s=%s' % (package, label))

    def shadowSource(self, name, version, targetLabel):
        """
        Create a shadow of a conary source package.  Similar to the
        C{cvc shadow} command.
        @param name: package to shadow
        @type name: string
        @param version: version of package to shadow
        @type version: string or B{opaque} C{conary.versions.Version}
        @param targetLabel: label on which to create shadow
        @type targetLabel: string or B{opaque} conary.versions.Label
        @return: C{(name, version, flavor)} tuple specifying the newly-created
        shadow.
        @rtype: (string, string, string)
        """
        version = self._getVersion(version)
        flavor = self._getFlavor()
        targetLabel = self._getLabel(targetLabel)
        item = self._getConaryClient().createShadowChangeSet(
                        str(targetLabel),
                        [(name, version, flavor)])
        if item:
            skipped, cs = item
            if cs and not cs.isEmpty():
                self._getRepositoryClient().commitChangeSet(cs)
            if skipped:
                return skipped[0]
            else:
                return self._troveTupToStrings(
                    *cs.iterNewTroves().next().getNewNameVersionFlavor())
        else:
            return False

    #pylint: disable-msg=R0913
    # better than self, troveTup, targetDir
    def checkoutBinaryPackage(self, name, version, flavor, targetDir,
                              quiet=True):
        """
        Check out the contents of a binary package into a directory
        with a minimal derived recipe written and a binary checkout
        in the C{_ROOT_} directory to make modifying the derived
        package easier.  Does not commit the derived package.
        @param name: package to check out
        @type name: string
        @param version: version of package to check out
        @type version: string or B{opaque} C{conary.versions.Version}
        @param flavor: conary flavor
        @type flavor: string or B{opaque} conary.deps.deps.Flavor
        @param targetDir: subdirectory into which to check out the package,
        defaults to C{package}
        @type targetDir: string
        """
        version = self._versionToString(version)
        flavor = self._flavorToString(flavor)
        cfg = self.getConaryConfig()
        if quiet:
            callback = _QuietUpdateCallback()
        else:
            callback = None
        cfg = copy.deepcopy(cfg)
        cfg.root = targetDir
        updatecmd.doUpdate(cfg, '%s=%s[%s]' % (name, version, flavor),
                           callback=callback, depCheck=False)



#pylint: disable-msg=C0103,R0901,W0221,R0904
# "The creature can't help its ancestry"
class _QuietUpdateCallback(checkin.CheckinCallback):
    """
    Make checkout a bit quieter
    """
    def setUpdateJob(self, *args, **kw):
        'stifle update announcement for extract'
        pass

