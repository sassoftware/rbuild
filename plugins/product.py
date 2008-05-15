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
        while not os.path.exists(curDir + '/RBUILD') and curDir != '/':
            curDir = os.path.dirname(curDir)
        if curDir == '/':
            return None
        productStore =  DirectoryBasedProductStore(self._handle,
                                                   curDir + '/RBUILD')
        if os.path.exists('.stage'):
            stageName = open('.stage').read(1024).split('\n', 1)[0]
            productStore.setActiveStageName(stageName)
        return productStore

    def getProductStoreFromDirectory(self, directoryName):
        return DirectoryBasedProductStore(self._handle, directoryName)

class DirectoryBasedProductStore(object):
    def __init__(self, handle, baseDirectory):
        self._handle = handle
        self._baseDirectory = os.path.realpath(baseDirectory)
        self._currentStage = None
        if not os.path.exists(baseDirectory + '/product-definition.xml'):
            raise errors.RbuildError(
                            'No product checkout at %r' % baseDirectory)

    def getBaseDirectory(self):
        return self._baseDirectory

    def update(self):
        return self._handle.facade.conary.updateCheckout(self._baseDirectory)

    def get(self):
        path = self._baseDirectory + '/product-definition.xml'
        return proddef.ProductDefinition(fromStream=open(path))

    def getActiveStageName(self):
        return self._currentStage

    def setActiveStageName(self, stageName):
        self._currentStage = stageName

    def getRmakeConfigPath(self):
        return self._baseDirectory + '/rmakerc'
