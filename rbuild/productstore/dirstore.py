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

from conary.lib import cfg
from conary.lib import cfgtypes

from rpath_common.proddef import api1 as proddef

from rbuild import errors
from rbuild.productstore.abstract import ProductStore

def getDefaultProductDirectory(dirName=None):
    """
    Starting at the current directory, look up the directory tree
    for a product checkout.
    @param dirName: (current working directory) Optional directory name
    to search
    @return: directory name, or C{None} if no checkout found.
    @rtype: str
    """
    if not dirName:
        dirName = os.getcwd()
    productPath = dirName \
                    + '/.rbuild/product-definition/product-definition.xml'
    while not os.path.exists(productPath) and dirName != '/':
        dirName = os.path.dirname(dirName)
        productPath = dirName \
                    + '/.rbuild/product-definition/product-definition.xml'
    if dirName == '/':
        dirName = None
    return dirName

def getStageNameFromDirectory(dirName=None):
    '''
    Returns the stage name associated with a directory, or None if
    no stage is found above the current directory.
    @param dirName: name of directory to search
    @return: name of stage, or None
    @rtype: str
    '''
    stageName = None
    if dirName is None:
        dirName = os.getcwd()
    else:
        dirName = os.path.abspath(dirName)
    while (stageName is None and not os.path.exists(dirName + '/.rbuild')
           and dirName != '/'):
        stageCandidate = dirName + '/.stage'
        if os.path.exists(stageCandidate):
            # found our current stage; might have been called
            # from a stage directory or a package directory
            stageName = open(stageCandidate).read(1024).split('\n', 1)[0]
            break
        dirName = os.path.dirname(dirName)
    return stageName


class CheckoutProductStore(ProductStore):
    def __init__(self, handle, baseDirectory=None):
        ProductStore.__init__(self, handle)
        productDirectory = getDefaultProductDirectory(baseDirectory)
        if productDirectory is None:
            if baseDirectory is None:
                raise errors.RbuildError('Could not find product directory')
            else:
                raise errors.RbuildError("No product directory at '%s'"
                                         %baseDirectory)
        self._baseDirectory = os.path.realpath(productDirectory)
        self._testProductDirectory(productDirectory)
        stageName = getStageNameFromDirectory(os.getcwd())
        if stageName is not None:
            # Cannot load product yet, so cannot validate
            self._currentStage = stageName

    def getProduct(self):
        path = (self.getProductDefinitionDirectory()
                + '/product-definition.xml')
        return proddef.ProductDefinition(fromStream=open(path))

    def update(self):
        """
        This is the only acceptable way to update a product definition
        checkout, because it invalidates the cached copy of the data.
        """
        if not self._handle.facade.conary.updateCheckout(
            self.getProductDefinitionDirectory()):
            raise errors.RbuildError('Failed to update product definition')
        ProductStore.update(self)


    @staticmethod
    def _testProductDirectory(baseDirectory):
        """
        Test to see whether a product directory has been checked out
        @param baseDirectory: name of product directory
        @type baseDirectory: string
        @raise errors.RbuildError: If no product definition is checked out
        in an .rbuild directory under baseDirectory
        """
        productDefPath = (baseDirectory +
                          '/.rbuild/product-definition/product-definition.xml')
        if not os.path.exists(productDefPath):
            raise errors.RbuildError(
                            'No product directory at %r' % baseDirectory)

    def getProductDefinitionDirectory(self):
        return self._baseDirectory + '/.rbuild/product-definition'

    def getPlatformDefinitionDirectory(self):
        '''
        Get the directory for the platform definition created from the
        product definition (not the platform definition on which the
        product definition is based).
        @return: full path to directory
        @rtype: str
        '''
        return self._baseDirectory + '/.rbuild/platform-definition'

    def getStageDirectory(self, stageName):
        stageDirectory = '%s/%s' % (self._baseDirectory, stageName)
        if not os.path.exists(stageDirectory):
            raise errors.RbuildError('Stage directory for %r'
                                     ' does not exist' % stageName)
        return stageDirectory

    def getEditedRecipeDicts(self, stageName = None):
        """
        @param stageName: (None) Stage name to inspect relative to the
        current product.
        @type stageName: string
        @return: Tuple of two C{dicts}, the first containing a map
        from package name to recipe path and the second containing
        a map from group name to recipe path.
        """
        packageDict = {}
        groupDict = {}
        conaryFacade = self._handle.facade.conary
        if stageName is None:
            stageName = self.getActiveStageName()
        if stageName is not None:
            stageDir = self.getStageDirectory(stageName)
            for dirName in os.listdir(stageDir):
                packageDir = '%s/%s' % (stageDir, dirName)
                if os.path.exists(packageDir + '/CONARY'):
                    packageName = conaryFacade.getNameForCheckout(packageDir)
                    recipePath = '%s/%s.recipe' % (packageDir,
                                                   packageName)
                    if conaryFacade.isGroupName(packageName):
                        groupDict[packageName] = recipePath
                    else:
                        packageDict[packageName] =  recipePath
        return packageDict, groupDict

    def getRbuildConfigData(self):
        return file(self.getRbuildConfigPath()).read()

    def getRbuildConfigPath(self):
        return self._baseDirectory + '/.rbuild/rbuildrc'

    def getRmakeConfigData(self):
        return file(self.getRmakeConfigPath()).read()

    def getRmakeConfigPath(self):
        return self.getProductDefinitionDirectory() + '/rmakerc'

    def getStatus(self, key):
        return self._getStatusStore()[key]

    def setStatus(self, key, value):
        statusStore = self._getStatusStore()
        statusStore.setValue(key, value)
        statusStore.save()

    def _getStatusStore(self):
        return _FileStatusStore(self._baseDirectory + '/.rbuild/status')

    def checkoutPlatform(self):
        """
        Create a checkout from this product of the platform derived from
        the product.  This is not a checkout of the platform on which
        this product is based.
        """
        platformLabel = self._handle.product.getProductDefinitionLabel()
        self._handle.facade.conary.checkout('platform-definition',
                            platformLabel,
                            targetDir=self.getPlatformDefinitionDirectory())


class _FileStatusStore(cfg.ConfigFile):
    # Note that after rbuild 1.0, if we want to change this file format,
    # we will need to convert existing data.  Since that would create a
    # "flag day", we should only do that for a new major version
    # unless there is a strong reason otherwise.

    packageJobId  = cfgtypes.CfgInt
    groupJobId  = cfgtypes.CfgInt
    imageJobId  = cfgtypes.CfgInt

    def __init__(self, baseFile):
        cfg.ConfigFile.__init__(self)
        self.read(baseFile, exception=False)
        self._baseFile = baseFile

    def save(self):
        self.writeToFile(self._baseFile)
