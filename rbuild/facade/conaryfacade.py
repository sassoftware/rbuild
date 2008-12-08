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
import itertools
import os
import stat
import types
import urlparse

from conary import conarycfg
from conary import conaryclient
from conary.conaryclient import cmdline
from conary import checkin
from conary.deps import deps
from conary import state
from conary import trove
from conary import updatecmd
from conary import versions
from conary.lib import util

from conary.build import loadrecipe
from conary.build import use
from conary.build import errors as builderrors

from rbuild import errors


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
        self._initializedFlavors = False

#{ Private Methods
    def _parseRBuilderConfigFile(self, cfg):
        """
        Include conary configuration file provided by rBuilder
        @param cfg: configuration file to add rbuilder configuration
        data to.
        """
        serverUrl = self._handle.getConfig().serverUrl
        if serverUrl:
            hostname = urlparse.urlparse(serverUrl)[1]
            if hostname not in ['www.rpath.com', 'www.rpath.org']:
                cfg.includeConfigFile(serverUrl + '/conaryrc')

    def _initializeFlavors(self):
        if not self._initializedFlavors:
            self.getConaryConfig().initializeFlavors()
            self._initializedFlavors = True

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
        if isinstance(version, types.StringTypes):
            return versions.VersionFromString(str(version))
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
        if isinstance(label, types.StringTypes):
            return versions.Label(str(label))
        return label

    @staticmethod
    def _getFlavor(flavor=None, keepNone=False):
        """
        Converts a version string into an B{opaque} Conary flavor object
        or returns the B{opaque} flavor object.
        @param flavor: conary flavor
        @type flavor: string or B{opaque} conary.deps.deps.Flavor
        @param keepNone: if True, leave None objects as None instead
        of converting to empty flavor
        @type keepNone: boolean
        @return: B{opaque} Conary flavor object
        @rtype: conary.deps.deps.Flavor
        """
        if flavor is None:
            if keepNone:
                return None
            else:
                return(deps.Flavor())
        if isinstance(flavor, types.StringTypes):
            return deps.parseFlavor(str(flavor), raiseError=True)
        return flavor

    def _findTrovesFlattened(self, specList, labelPath=None,
                             allowMissing=False):
        results = self._findTroves(specList, labelPath=labelPath, 
                                   allowMissing=allowMissing)
        return list(itertools.chain(*results.values()))

    def _findTroves(self, specList, labelPath=None,
                    allowMissing=False):
        newSpecList = []
        specMap = {}
        for spec in specList:
            if not isinstance(spec, tuple):
                newSpec = cmdline.parseTroveSpec(spec)
            else:
                newSpec = spec
            newSpecList.append(newSpec)
            specMap[newSpec] = spec
        repos = self._getRepositoryClient()
        if isinstance(labelPath, (tuple, list)):
            labelPath = [ self._getLabel(x) for x in labelPath ]
        elif labelPath:
            labelPath = self._getLabel(labelPath)

        results = repos.findTroves(labelPath, newSpecList,
                                   allowMissing=allowMissing)
        return dict((specMap[x[0]], x[1]) for x in results.items())

    def _findTrove(self, name, version, flavor=None, labelPath=None,
                   allowMissing=False):
        #pylint: disable-msg=R0913
        # findTrove really needs all these arguments to pass through
        """
        Gets a reference to a trove in the repository.
        @param name: package to find
        @type name: string
        @param version: version of package to find
        @type version: string or C{conary.versions.Version} B{opaque}
        @param flavor: flavor of package to find (optional)
        @type flavor: string or C{deps.Flavor} B{opaque}
        @param labelPath: label(s) to find package on
        @type labelPath: None, conary.versions.Label, or list of
        conary.versions.Label
        @param allowMissing: if True, allow None as a return value if 
        the package
        was not found.
        @return: C{(name, version, flavor)} tuple.
        Note that C{version} and C{flavor} objects are B{opaque}.
        @rtype: (string, conary.versions.Version conary.deps.deps.Flavor)
        """
        repos = self._getRepositoryClient()
        flavor = self._getFlavor(flavor)
        results = repos.findTroves(labelPath, [(name, version, flavor)],
                                   allowMissing=allowMissing)
        if not results:
            return None
        troveTup, = results[name, version, flavor]
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
        flavor = cls._flavorToString(flavor)
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
            #pylint: disable-msg=E1101
            # pylint does not understand config objects very well
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
        checkin.checkout(self._getRepositoryClient(), cfg,
                         targetDir, ['%s=%s' % (package, label)])

    def refresh(self, targetDir=None):
        """
        Refresh the checked-out sources for a conary source package.
        @param targetDir: checkout directory to refresh
        @type targetDir: string
        """
        cfg = self.getConaryConfig()
        self._initializeFlavors()
        use.setBuildFlagsFromFlavor(None, cfg.buildFlavor, False)
        return checkin.refresh(self._getRepositoryClient(), cfg,
                               dirName=targetDir)

    def updateCheckout(self, targetDir):
        """
        Update a subdirectory containing a checkout of a conary
        source package.  Similar to the C{cvc update} command.
        @param targetDir: subdirectory containing package to update
        @type targetDir: string
        @return: Status
        @rtype: bool
        """
        # Conary likes absolute paths RBLD-137
        targetDir = os.path.abspath(targetDir)
        try:
            return checkin.nologUpdateSrc(self._getRepositoryClient(),
                                          [targetDir])
        except builderrors.UpToDate:
            # The end result is an up to date checkout, so ignore the exception
            return True
        except builderrors.CheckinError, e:
            # All other exceptions are deemed failures
            raise errors.RbuildError(str(e))
        except AttributeError:
            return checkin.updateSrc(self._getRepositoryClient(), [targetDir])

    def getCheckoutStatus(self, targetDir):
        """
        Create summary of changes regarding all files in a directory
        as a list of C{(I{status}, I{filename})} tuples where
        C{I{status}} is a single character describing the status
        of the file C{I{filename}}:
         - C{?}: File not managed by Conary
         - C{A}: File added since last commit (or since package created if no commit)
         - C{M}: File modified since last commit
         - C{R}: File removed since last commit
        @param targetDir: name of directory for which to fetch status.
        @type targetDir: string
        @return: lines of text describing differences
        @rtype: list
        """
        return checkin.generateStatus(self._getRepositoryClient(),
                                      dirName=targetDir)

    def getCheckoutLog(self, targetDir, newerOnly=False, versionList=None):
        """
        Returns list of lines of log messages relative to the specified
        targetDirectory.
        @param targetDir: name of directory for which to fetch status.
        @type targetDir: string
        @param newerOnly: (C{False}) whether to return only log messages
        newer than the current contents of the checkout.
        @type newerOnly: bool
        @param versionList: (C{None}) if set, a list of versions for
        which to return log messages.  If C{None}, return all log
        messages.
        @type versionList: list of strings or (opaque) conary version objects
        @return: list of strings
        """
        repos, sourceState = self._getRepositoryStateFromDirectory(targetDir)
        troveName = sourceState.getName()

        if versionList is None:
            if newerOnly:
                versionList = self._getNewerRepositoryVersions(targetDir)
            else:
                versionList = self._getRepositoryVersions(targetDir)
        else:
            versionList = [self._getVersion(x) for x in versionList]

        emptyFlavor = deps.Flavor()
        nvfList = [(troveName, v, emptyFlavor) for v in versionList]
        troves = repos.getTroves(nvfList)

        return [message for message in checkin.iterLogMessages(troves)]

    def iterRepositoryDiff(self, targetDir, lastver=None):
        """
        Yields lines of repository diff output relative to the
        specified targetDirectory.
        @param targetDir: name of directory for which to fetch status.
        @type targetDir: string
        @param lastver: (C{None}) None for diff between directory and
        latest version in repository, otherwise a string or (opaque)
        conary version object specifying the repository version against
        which to generated the diff.
        @return: yields strings
        """
        repos, sourceState = self._getRepositoryStateFromDirectory(targetDir)
        troveName = sourceState.getName()
        ver = sourceState.getVersion()
        label = ver.branch().label()

        if lastver is None:
            lastver = self._getNewerRepositoryVersions(targetDir)[-1]
        else:
            lastver = self._getVersion(lastver)

        for line in checkin._getIterRdiff(repos, label, troveName,
                                          ver.asString(), lastver.asString()):
            yield line

    def iterCheckoutDiff(self, targetDir):
        """
        Yields lines of checkout diff output relative to the
        specified targetDirectory.
        @param targetDir: name of directory for which to fetch status.
        @type targetDir: string
        @return: yields strings
        """
        repos, sourceState = self._getRepositoryStateFromDirectory(targetDir)
        ver = sourceState.getVersion()

        i = checkin._getIterDiff(repos, ver.asString(),
            pathList=None, logErrors=False, dirName=targetDir)
        if i not in (0, 2):
            # not an "error" case, so i really is an iterator
            for line in i:
                yield line

    def _getNewerRepositoryVersionStrings(self, targetDir):
        '''
        Returns list of versions from the repository that are newer than the checkout
        @param targetDir: directory containing Conary checkout
        @return: list of version strings
        '''
        return [self._versionToString(x)
                for x in self._getNewerRepositoryVersions(targetDir)]

    def _getNewerRepositoryVersions(self, targetDir):
        '''
        Returns list of versions from the repository that are newer than the checkout
        @param targetDir: directory containing Conary checkout
        @return: list of C{conary.versions.Version}
        '''
        _, sourceState = self._getRepositoryStateFromDirectory(targetDir)
        troveVersion = sourceState.getVersion()
        #pylint: disable-msg=E1103
        # we know that ver does have an isAfter method
        return [ver for ver in self._getRepositoryVersions(targetDir)
                if ver.isAfter(troveVersion)]

    def _getRepositoryVersions(self, targetDir):
        '''
        List of versions of the this package checked into the repository
        @param targetDir: directory containing Conary checkout
        @return: list of C{conary.versions.Version}
        '''
        repos, sourceState = self._getRepositoryStateFromDirectory(targetDir)
        branch = sourceState.getBranch()
        troveName = sourceState.getName()
        verList = repos.getTroveVersionsByBranch({troveName: {branch: None}})
        if verList:
            verList = verList[troveName].keys()
            verList.sort()
            verList.reverse()
        else:
            verList = []
        return verList

    def _getRepositoryStateFromDirectory(self, targetDir):
        '''
        Create repository and state objects for working with a checkout
        @param targetDir: directory containing Conary checkout
        '''
        repos = self._getRepositoryClient()
        conaryState = state.ConaryStateFromFile(targetDir + '/CONARY', repos)
        sourceState = conaryState.getSourceState()
        return repos, sourceState


    @staticmethod
    def isConaryCheckoutDirectory(targetDir):
        '''
        Return whether a directory contains a CONARY file
        @param targetDir: directory containing Conary checkout
        '''
        return os.path.exists(os.sep.join((targetDir, 'CONARY')))



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
        or pre-existing shadow.
        @rtype: (string, string, string)
        """
        version = self._getVersion(version)
        flavor = self._getFlavor()
        targetLabel = self._getLabel(targetLabel)
        results = self._getConaryClient().createShadowChangeSet(
                        str(targetLabel),
                        [(name, version, flavor)])
        if not results:
            return False
        return self._commitShadowChangeSet(results[0], results[1])[0]

    def shadowSourceForBinary(self, name, version, flavor, targetLabel):
        version = self._getVersion(version)
        flavor = self._getFlavor(flavor)
        targetLabel = self._getLabel(targetLabel)
        client = self._getConaryClient()
        results = client.createShadowChangeSet(
                        str(targetLabel),
                        [(name, version, flavor)],
                        branchType=client.BRANCH_SOURCE)
        if not results:
            return False
        return self._commitShadowChangeSet(results[0], results[1])[0]

    def _commitShadowChangeSet(self, existingShadow, cs):
        if cs and not cs.isEmpty():
            self._getRepositoryClient().commitChangeSet(cs)
        allTroves = []
        if existingShadow:
            allTroves.extend(self._troveTupToStrings(*x)
                             for x in existingShadow)
        if cs:
            allTroves.extend(
                        self._troveTupToStrings(*x.getNewNameVersionFlavor())
                        for x in cs.iterNewTroveList())
        return allTroves

    #pylint: disable-msg=R0913
    # too many args, but still better than self, troveTup, targetDir
    def checkoutBinaryPackage(self, name, version, flavor, targetDir,
            quiet=True, tagScript=None):
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
        @param quiet: (C{True}) determines whether to print update status
        during the operation.
        @type quiet: bool
        @param tagScript: If not C{None}, write tag scripts to this file
        instead of running them in-place.
        @type tagSCript: str
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
                callback=callback, depCheck=False, tagScript=tagScript)

    def _findPackageInGroups(self, groupList, packageName):
        repos = self._getRepositoryClient()
        groupList = [ (str(x[0]), str(x[1]), self._getFlavor(x[2],
                                                             keepNone=True))
                      for x in groupList ]
        results = repos.findTroves(None, groupList, None)
        troveTups = list(itertools.chain(*results.itervalues()))
        if not troveTups:
            return []
        # we will get multiple flavors here.  We only want those
        # flavors of these groups that have been built most recently
        # to be taken into account
        maxVersion = sorted(troveTups, key=lambda x:x[1])[-1][1]
        troveTups = [ x for x in troveTups if x[1] == maxVersion ]

        troves = repos.getTroves(troveTups, withFiles=False)
        matchingTroveList = []
        for trv in troves:
            for troveTup in trv.iterTroveList(weakRefs=True,
                                              strongRefs=True):
                if troveTup[0] == packageName:
                    matchingTroveList.append(troveTup)
        return matchingTroveList

    def _overrideFlavors(self, baseFlavor, flavorList):
        baseFlavor = self._getFlavor(baseFlavor)
        return [ str(deps.overrideFlavor(baseFlavor, self._getFlavor(x)))
                 for x in flavorList ]

    def _getFlavorArch(self, flavor):
        flavor = self._getFlavor(flavor)
        return deps.getMajorArch(flavor)

    def _getShortFlavorDescriptors(self, flavorList):
        if not flavorList:
            return {}

        descriptions = deps.getShortFlavorDescriptors(
                                  [ self._getFlavor(x) for x in flavorList ])
        return dict((str(x[0]), x[1]) for x in descriptions.items())

    def _loadRecipeClassFromCheckout(self, recipePath):
        directory = os.path.dirname(recipePath)
        repos, sourceState = self._getRepositoryStateFromDirectory(directory)

        cfg = self.getConaryConfig()
        self._initializeFlavors()
        loader = loadrecipe.RecipeLoader(recipePath, cfg=cfg,
                                     repos=repos,
                                     branch=sourceState.getBranch(),
                                     buildFlavor=cfg.buildFlavor)
        return loader.getRecipe()

    def _removeNonRecipeFilesFromCheckout(self, recipePath):
        recipeDir = os.path.dirname(recipePath)
        recipeName = os.path.basename(recipePath)
        repos =  self._getRepositoryClient()
        statePath = os.path.join(recipeDir, 'CONARY')
        conaryState = state.ConaryStateFromFile(statePath, repos)
        sourceState = conaryState.getSourceState()

        for (pathId, path, _, _) in list(sourceState.iterFileList()):
            if path == recipeName:
                continue
            path = os.path.join(recipeDir, path)
            sourceState.removeFile(pathId)

            if util.exists(path):
                statInfo = os.lstat(path)
                try:
                    if statInfo.st_mode & stat.S_IFDIR:
                        os.rmdir(path)
                    else:
                        os.unlink(path)
                except OSError, e:
                    self._handle.ui.warning(
                                "cannot remove %s: %s", path, e.strerror)
        conaryState.write(statePath)

    @staticmethod
    def getNameForCheckout(checkoutDir):
        conaryState = state.ConaryStateFromFile(checkoutDir + '/CONARY')
        return conaryState.getSourceState().getName().split(':', 1)[0]

    @staticmethod
    def isGroupName(packageName):
        return trove.troveIsGroup(packageName)

    def promoteGroups(self, groupList, fromTo):
        """
        Promote the troves in C{groupList} using the promote map in
        C{fromTo}. The former should be a list of trove tuples, and the
        latter a dictionary mapping of labels (C{from: to}).

        @param groupList: List of group trove tuples to promote
        @type  groupList: [(name, version, flavor)]
        @param fromTo: Mapping of labels to execute promote on
        @type  fromTo: {from: to}
        """
        def getLabelOrBranch(label):
            if isinstance(label, types.StringTypes):
                if label.startswith('/'):
                    return self._getVersion(label)
                else:
                    return self._getLabel(label)
            return label

        promoteMap = dict((self._getLabel(fromLabel), getLabelOrBranch(toLabel))
            for (fromLabel, toLabel) in fromTo.iteritems())

        client = self._getConaryClient()
        success, cs = client.createSiblingCloneChangeSet(promoteMap,
            groupList, cloneSources=True)

        if not success:
            raise errors.RbuildError('Promote failed.')
        else:
            packageList = [ x.getNewNameVersionFlavor()
                           for x in cs.iterNewTroveList() ]
            packageList = [ (str(x[0]), str(x[1]), str(x[2])) 
                            for x in packageList ]
            self._getRepositoryClient().commitChangeSet(cs)
            return packageList

    def getLatestPackagesOnLabel(self, label, keepComponents=False,
      keepGroups=False):
        client = self._getConaryClient()
        label = self._getLabel(label)
        results = client.getRepos().getTroveLatestByLabel(
            {None: {label: [None]}})

        packages = []
        for name, versiondict in results.iteritems():
            if ':' in name and not keepComponents:
                continue
            elif trove.troveIsGroup(name) and not keepGroups:
                continue

            for version, flavors in versiondict.iteritems():
                for flavor in flavors:
                    packages.append((name, version, flavor))
        return packages


#pylint: disable-msg=C0103,R0901,W0221,R0904
# "The creature can't help its ancestry"
class _QuietUpdateCallback(checkin.CheckinCallback):
    """
    Make checkout a bit quieter
    """
    #pylint: disable-msg=W0613
    # unused arguments
    # implements an interface that may pass arguments that need to be ignored
    def setUpdateJob(self, *args, **kw):
        #pylint: disable-msg=C0999
        # arguments not documented: implements interface, ignores parameters
        'stifle update announcement for extract'
        return
