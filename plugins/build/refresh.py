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
import os.path

from rbuild import errors

def refreshPackages(handle, packageList):
    _refreshPackages(handle, packageList) 

def refreshAllPackages(handle):
    _refreshPackages(handle)

def _refreshPackages(handle, packageList=None):
    conaryFacade = handle.facade.conary

    if not packageList:
        # Get a list of all package paths
        # Note: groups cannot be refreshed, so ignore them
        packageDict, _ = handle.productStore.getEditedRecipeDicts()
        packagePaths = packageDict.values()
        for packagePath in packagePaths:
            packageDir = os.path.dirname(packagePath)
            conaryFacade.refresh(targetDir=packageDir)
    else:
        for package in packageList:
            packageDir = handle.productStore.getPackagePath(package)
            conaryFacade.refresh(targetDir=packageDir)
