#
# Copyright (c) SAS Institute Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


import os

from conary.lib import cfg
from conary.lib import cfgtypes

from rpath_proddef import api1 as proddef

from rbuild import errors
from rbuild.productstore.abstract import ProductStore


def getDefaultProductDirectory(dirName=None, error=False):
    """
    Starting at the current directory, look up the directory tree
    for a product checkout.
    @param dirName: (current working directory) Optional directory name
    to search
    @param error: (C{False}) if set to C{True}, raise 
    C{MissingProductStoreError} if no product directory is found
    @return: directory name, or C{None} if no checkout found.
    @rtype: str
    @raise MissingProductStoreError: if C{error=True} and no product
    directory is found.
    """
    if not dirName:
        dirName = os.getcwd()
    elif not os.path.exists(dirName):
        raise errors.MissingProductStoreError(dirName)
    origDirName = dirName

    productPath = dirName \
                    + '/.rbuild/product-definition/product-definition.xml'
    while not os.path.exists(productPath) and dirName != '/':
        dirName = os.path.dirname(dirName)
        productPath = dirName \
                    + '/.rbuild/product-definition/product-definition.xml'
    if dirName == '/':
        dirName = None

    if dirName is None and error is not False:
        raise errors.MissingProductStoreError(origDirName)

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
    #pylint: disable-msg=R0904
    # See ProductStore -- this is just a big class
    def __init__(self, handle=None, baseDirectory=None):
        ProductStore.__init__(self, handle)
        productDirectory = getDefaultProductDirectory(baseDirectory)
        if productDirectory is None:
            if baseDirectory is None:
                raise errors.RbuildError('Could not find product directory')
            else:
                raise errors.RbuildError("No product directory at '%s'"
                                         %baseDirectory)
        self._baseDirectory = os.path.realpath(productDirectory)
        self._testProductDirectory(self._baseDirectory)
        stageName = getStageNameFromDirectory(os.getcwd())
        if stageName is not None:
            # Cannot load product yet, so cannot validate
            self._currentStage = stageName
        self.statusStore = None            

    def getBaseDirectory(self):
        return self._baseDirectory

    def getProduct(self):
        path = (self.getProductDefinitionDirectory()
                + '/product-definition.xml')
        return proddef.ProductDefinition(fromStream=open(path))

    def getProductVersion(self):
        return self.getProduct().getProductVersion()
    
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

    def getStageDirectory(self, stageName=None):
        """
        Get the absolute directory associated with a given stage name.
        @param stageName: stage name, or None to use the active stage.
        @type stageName: string
        @return: string of absolute directory corrosponding to C{stageName},
        if none found, then return None.
        @rtype: string or None
        """
        if stageName is None:
            stageName = self.getActiveStageName()
        if stageName is not None:
            stageDirectory = '%s/%s' % (self._baseDirectory, stageName)
            if not os.path.exists(stageDirectory):
                raise errors.RbuildError('Stage directory for %r'
                                         ' does not exist' % stageName)
            return stageDirectory
        else:
            return None

    def getCheckoutDirectory(self, packageName):
        """
        Provides a canonical directory name relative to the current
        active stage for a package checkout.  This directory may or
        may not exist.
        @param packageName: name of package
        @return: string containing full directory name for checkout
        """
        # Note: may have an additional keyword paramater added later
        # for handling the non-default label case, where the directory
        # into which to check out would be different
        return os.path.normpath('%s/%s'
            %(self.getStageDirectory(), packageName))

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
        stageDir = self.getStageDirectory(stageName)
        if stageDir is not None:
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

    def getPackagePath(self, packageName, stageName=None):
        """
        Get the absolute filesystem path for the checked out package name.

        @param packageName: package name
        @type packageName: string
        @param stageName: stage name to search for C{packageName}, or None to
        use current stage.
        @type stageName: string
        @return: absolute path for C{packageName}, or None if no path is
        found.
        @rtype: string
        """
        conaryFacade = self._handle.facade.conary
        stageDir = self.getStageDirectory(stageName)
        if stageDir is not None:
            for dirName in os.listdir(stageDir):
                packageDir = '%s/%s' % (stageDir, dirName)
                if os.path.exists(packageDir + '/CONARY'):
                    if packageName == \
                        conaryFacade.getNameForCheckout(packageDir):
                        return packageDir
        return None                        

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
        if self.statusStore is None:
            for stageName in self.iterStageNames():
                stageKey = "%s-%s" % (stageName, "releaseId")
                setattr(_FileStatusStore, stageKey, cfgtypes.CfgInt)
            self.statusStore = _FileStatusStore(self._baseDirectory
                    + '/.rbuild/status')

        return self.statusStore

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
    #
    #pylint: disable-msg=R0904
    # too many public methods: "the creature can't help its ancestry"

    packageJobId  = cfgtypes.CfgInt
    groupJobId  = cfgtypes.CfgInt
    imageJobId  = cfgtypes.CfgInt

    def __init__(self, baseFile):
        cfg.ConfigFile.__init__(self)
        self.read(baseFile, exception=False)
        self._baseFile = baseFile

    def save(self):
        self.writeToFile(self._baseFile)

    def __setitem__(self, key, value):

        cfg.ConfigFile.__setitem__(self, key, value)
