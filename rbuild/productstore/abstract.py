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
import os

from rpath_common.proddef import api1 as proddef

from rbuild import errors

class ProductStore(object):
    """
    Base product store class, containing methods common to all product
    stores.
    """

    def __init__(self, handle):
        self._handle = handle
        self._currentStage = None

    def getProduct(self):
        return proddef.ProductDefinition()

    def update(self):
        """
        This is the only acceptable way to update a product definition
        because it invalidates any cached copy of the data.
        """
        self._handle.product = self.getProduct()

    def iterStageNames(self):
        return (x.name for x in self._handle.product.getStages())

    def getNextStageName(self, stageName):
        stageNames = list(self.iterStageNames())
        stageIdx = stageNames.index(stageName)
        if stageIdx + 1 == len(stageNames):
            return None
        return stageNames[stageIdx + 1]

    def getActiveStageName(self):
        if self._currentStage is None:
            raise errors.RbuildError('No current stage (setActiveStageName)')
        return self._currentStage

    def getActiveStageLabel(self):
        return self._handle.product.getLabelForStage(self.getActiveStageName())

    def setActiveStageName(self, stageName):
        self.checkStageIsValid(stageName)
        self._currentStage = stageName

    def checkStageIsValid(self, stageName):
        stageNames = [ str(x.name) for x in self._handle.product.getStages() ]
        if stageName not in stageNames:
            raise errors.RbuildError('Unknown stage %r' % stageName)

    def getGroupFlavors(self):
        product = self._handle.product
        groupFlavors = [ (str(x.getBuildImageGroup()),
                          str(x.getBuildBaseFlavor()))
                         for x in product.getBuildDefinitions() ]
        fullFlavors = self._handle.facade.conary._overrideFlavors(
                                             str(product.getBaseFlavor()),
                                             [x[1] for x in groupFlavors])
        fullFlavors = [ self._addInExtraFlavor(x) for x in fullFlavors ]
        return [(x[0][0], x[1]) for x in zip(groupFlavors, fullFlavors)]

    # temporary hack until RPCL-13 is complete
    def _addInExtraFlavor(self, flavor):
        majorArch = self._handle.facade.conary._getFlavorArch(flavor)
        if majorArch == 'x86':
            extraFlavor = ('~!grub.static'
                           ' is: x86(~i486,~i586,~i686,~cmov,~sse,~sse2)')
        else:
            extraFlavor = ('~grub.static is: x86_64'
                           ' x86(~i486,~i586,~i686,~cmov,~sse,~sse2)')
        return self._handle.facade.conary._overrideFlavors(flavor,
                                                           [extraFlavor])[0]


    def getPackageJobId(self):
        return self.getStatus('packageJobId')

    def getGroupJobId(self):
        return self.getStatus('groupJobId')

    def setPackageJobId(self, jobId):
        self.setStatus('packageJobId', jobId)

    def setGroupJobId(self, jobId):
        self.setStatus('groupJobId', jobId)

    def getStatus(self, key):
        raise errors.IncompleteInterfaceError(
            'rBuild status storage unsupported for this configuration')

    def setStatus(self, key, value):
        raise errors.IncompleteInterfaceError(
            'rBuild status storage unsupported for this configuration')

    def getRbuildConfigData(self):
        raise errors.IncompleteInterfaceError(
            'rBuild configuration data unsupported for this configuration')

    def getRbuildConfigPath(self):
        # could save self.getRbuildConfigData() to a temporary file
        raise errors.RbuildError(
            'Not Yet Implemented')

    def getRmakeConfigData(self):
        raise errors.IncompleteInterfaceError(
            'rMake configuration data unsupported for this configuration')

    def getRmakeConfigPath(self):
        # could save self.getRmakeConfigData() to a temporary file
        raise errors.RbuildError(
            'Not Yet Implemented')
