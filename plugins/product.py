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
from rbuild import pluginapi

class Product(pluginapi.Plugin):

    def getDefaultProductStore(self):
        curDir = os.getcwd()
        stageName = None
        while not os.path.exists(curDir + '/RBUILD') and curDir != '/':
            if stageName is None and os.path.exists(curDir + '/.stage'):
                # found our current stage; might have been called
                # from a stage directory or a package directory
                stageName = open('.stage').read(1024).split('\n', 1)[0]
            curDir = os.path.dirname(curDir)
        if curDir == '/':
            return None
        productStore =  self.getProductStoreFromDirectory(curDir)
        if stageName is not None:
            productStore.setActiveStageName(stageName)
        return productStore

    def getProductStoreFromDirectory(self, directoryName):
        return DirectoryBasedProductStore(self.handle, directoryName)

class DirectoryBasedProductStore(object):
    def __init__(self, handle, baseDirectory):
        self._handle = handle
        self._baseDirectory = os.path.realpath(baseDirectory)
        self._currentStage = None
        self._proddef = None
        self._testProductCheckout(baseDirectory)

    def _testProductCheckout(self, baseDirectory):
        """
        Test to see whether a product checkout exists
        @param baseDirectory: name of product directory
        @type baseDirectory: string
        @raise errors.rRbuildError: If no product checkout exists in an
        RBUILD directory under the product directory
        """
        if not os.path.exists(baseDirectory + '/RBUILD/product-definition.xml'):
            raise errors.RbuildError(
                            'No product checkout at %r' % baseDirectory)

    def getBaseDirectory(self):
        return self._baseDirectory

    def update(self):
        """
        This is the only acceptable way to update a product definition
        checkout, because it invalidates the cached copy of the data.
        """
        # After an update, expire any cache
        self._proddef = None
        return self._handle.facade.conary.updateCheckout(
            self._baseDirectory+'/RBUILD')

    def get(self):
        if self._proddef is None:
            path = self._baseDirectory + '/RBUILD/product-definition.xml'
            self._proddef = proddef.ProductDefinition(fromStream=open(path))
        return self._proddef

    def iterStageNames(self):
        return (x.name for x in self.get().getStages())

    def getActiveStageName(self):
        return self._currentStage

    def getActiveStageLabel(self):
        return self.get().getLabelForStage(self._currentStage)

    def setActiveStageName(self, stageName):
        self._currentStage = stageName

    def iterPackageDirsInStage(self, stageName = None):
        """
        Iterator which yields directory names containing Conary
        source checkouts for a specified stage (the default stage
        if not otherwise specified).
        @param stageName: (None) Stage name to inspect relative to the
        currentp product.
        @type stageName: string
        @return: iterator returning strings with directory names
        """
        if stageName is None:
            stageName = self.getActiveStageName()
        if stageName is not None:
            for dirName in os.listdir('%s/%s' %(
                                      self._baseDirectory, stageName)):
                packageDir = ('%s/%s' %(dirName, 'CONARY'))
                if os.path.exists(packageDir):
                    yield dirName

    def getRmakeConfigPath(self):
        return self._baseDirectory + '/RBUILD/rmakerc'
