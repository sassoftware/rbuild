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
    Checkout command and related utilities.
"""
import os
import tempfile

from conary.lib import util

from rpath_common import proddef

from rbuild import errors
from rbuild import pluginapi
from rbuild.pluginapi import command

class CheckoutCommand(command.BaseCommand):
    """
        Creates a working directory for working with the given product.

        Parameters: (repository namespace version|label)

        Example: checkout foresight.rpath.org fl 2
        Assuming that there were a product defined at
        foresight.rpath.org@fl:proddef-2, this would create a product for

    """
    commands = ['checkout']
    def runCommand(self, handle, _, args):
        if len(args) == 3:
            label, = self.requireParameters(args, ['label'])[1:]
            self.checkoutByLabelCommand(handle, label)
        else:
            params = self.requireParameters(args, ['repository',
                                                   'namespace', 'version'])
            repository, namespace, version = params[1:]
            self.checkoutCommand(handle, repository, namespace, version)

    def checkoutByLabelCommand(self, handle, label):
        #R0201: method could be a function
        #pylint: disable-msg=R0201
        productStore = handle.Checkout.getProductStoreByLabel(label)
        productStore.createCheckout()
        # if we didn't get an exception, the command succeeded.
        return 0

    def checkoutCommand(self, handle, repository, namespace, version):
        #R0201: method could be a function
        #pylint: disable-msg=R0201
        productStore = handle.Checkout.getProductStoreByParts(
                                            repository, namespace, version)
        productStore.createCheckout()
        # if we didn't get an exception, the command succeeded.
        return 0

class Checkout(pluginapi.Plugin):
    name = 'checkout'

    def registerCommands(self):
        self._handle.Commands.registerCommand(CheckoutCommand)

    def getProductStoreByParts(self, repository, namespace, version):
        labelStr = '%s@%s:proddef-%s' % (repository, namespace, version)
        return self.getProductStoreByLabel(labelStr)

    def getProductStoreByLabel(self, label):
        version = self._handle.facade.conary._findTrove(
                                        'product-definition:source',
                                        str(label))[1]
        return self.getProductStoreByVersion(version)

    def getProductStoreByVersion(self, version):
        return ProductStore(self._handle, version)


class ProductStore(object):
    def __init__(self, handle, version):
        self.handle = handle
        self.version = version
        self.product = None

    def createCheckout(self, checkoutDir=None):
        if checkoutDir is None:
            checkoutDir = tempfile.mkdtemp(dir=os.getcwd())
            tempDir = checkoutDir
        else:
            tempDir = None
            if not os.path.exists(checkoutDir):
                util.mkdirChain(checkoutDir)

        targetDir = checkoutDir + '/RBUILD'
        self.handle.facade.conary.checkout('product-definition', self.version,
                                           targetDir=targetDir)
        productFile = targetDir + '/product-definition.xml'
        self.product = self.getProductFromFile(productFile)
        if tempDir:
            checkoutDir = self.product.getProductShortname()
            if os.path.exists(checkoutDir):
                util.rmtree(tempDir)
                raise errors.RbuildError(
                                'Directory %r already exists.' % checkoutDir)
            os.rename(tempDir, checkoutDir)

        stages = self.product.getStages()
        for stage in stages:
            stageDir = checkoutDir + '/' + stage.name
            os.mkdir(stageDir)
            open(stageDir + '/.stage', 'w').write(stage.name + '\n')
        self.handle.getConfig().writeToFile(targetDir + '/rbuildrc')

    def getProductFromFile(self, path):
        self.product = proddef.ProductDefinition(fromStream=open(path))
        return self.product

    def getProduct(self):
        if self.product:
            return self.product
        fileObj = self.handle.facade.conary.getFileFromTrove(
                                               'product-definition:source',
                                               self.version,
                                               ['product-definition.xml'])
        self.product = proddef.ProductDefinition(fromStream=fileObj.get())
        return self.product
