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
init command and related utilities.
"""
import os
import tempfile

from conary.lib import util

from rpath_common.proddef import api1 as proddef

from rbuild import errors
from rbuild import pluginapi
from rbuild.pluginapi import command
from rbuild.productstore import dirstore

class InitCommand(command.BaseCommand):
    """
    Creates a working directory for working with the given product.

    Parameters: (repository namespace shortname version|label)

    Example: C{rbuild init foresight.rpath.org fl prod 2}
    Assuming that there were a product defined at
    foresight.rpath.org@fl:prod-2, this would create a product
    subdirectory tree representing the contents of that product
    definition.
    """

    commands = ['init']
    help = 'Create a directory for for working with a product'

    def runCommand(self, handle, _, args):
        if len(args) == 3:
            label, = self.requireParameters(args, ['label'])[1:]
            self._initByLabelCommand(handle, label)
        else:
            params = self.requireParameters(args, ['repository', 'version'])
            repository, version = params[1:]
            self._initCommand(handle, repository, version)

    @staticmethod
    def _initByLabelCommand(handle, label):
        version = handle.Init.getProductVersionByLabel(label)
        handle.Init.createProductDirectory(version)
        return 0

    @staticmethod
    def _initCommand(handle, repository, version):
        fullVersion = handle.Init.getProductVersionByParts(repository, version)
        handle.Init.createProductDirectory(fullVersion)
        return 0

class Init(pluginapi.Plugin):
    name = 'init'

    def registerCommands(self):
        self.handle.Commands.registerCommand(InitCommand)

    def getProductVersionByParts(self, repository, version):
        labelStr = self.handle.facade.rbuilder.getProductLabelFromNameAndVersion(
                                                        repository, version)
        return self.getProductVersionByLabel(labelStr)

    def getProductVersionByLabel(self, label):
        troveName = proddef.ProductDefinition.getTroveName() + ':source'
        version = self.handle.facade.conary._findTrove(
                                        troveName,
                                        str(label))[1]
        return str(version)

    def createProductDirectory(self, version, productDir=None):
        if productDir is None:
            productDir = tempfile.mkdtemp(dir=os.getcwd())
            tempDir = productDir
        else:
            tempDir = None

        try:
            util.mkdirChain(productDir + '/.rbuild')
            os.mkdir(productDir + '/.rbuild/tracebacks', 0700)

            targetDir = productDir + '/.rbuild/product-definition'
            self.handle.facade.conary.checkout('product-definition', version,
                                               targetDir=targetDir)
            handle = self.handle
            productStore = dirstore.CheckoutProductStore(handle, productDir)
            product = productStore.getProduct()
            if tempDir:
                productDir = '%s-%s' % (product.getProductShortname(),
                                        product.getProductVersion())
                if os.path.exists(productDir):
                    raise errors.RbuildError(
                                    'Directory %r already exists.' % productDir)
                os.rename(tempDir, productDir)
                tempDir = None
                targetDir = productDir + '/.rbuild/product-definition'
        finally:
            if tempDir:
                util.rmtree(tempDir)

        stages = product.getStages()
        for stage in stages:
            stageDir = productDir + '/' + stage.name
            os.mkdir(stageDir)
            open(stageDir + '/.stage', 'w').write(stage.name + '\n')
        self.handle.getConfig().writeCheckoutFile(productDir + '/.rbuild/rbuildrc')
        self.handle.ui.info('Created checkout for %s at %s', 
                             product.getProductDefinitionLabel(),
                             productDir)
        # get the versions that point to the real checkout now
        handle.productStore = dirstore.CheckoutProductStore(None, productDir)
        handle.product = handle.productStore.getProduct()
        return handle.productStore
