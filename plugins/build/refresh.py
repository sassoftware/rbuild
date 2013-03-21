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
