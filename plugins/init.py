#
# Copyright (c) rPath, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#


"""
init command and related utilities.
"""
import os
import tempfile

from conary.lib import util

from rpath_proddef import api1 as proddef

from rbuild import errors
from rbuild import pluginapi
from rbuild.pluginapi import command
from rbuild.productstore import dirstore

import rbuild.constants

class InitCommand(command.BaseCommand):
    """
    Creates a working directory for working with the given product.

    Parameters: (<project shortname> <version>|<label>)

    Example: C{rbuild init exampleprod 2}
    Assuming that there were a product defined at
    exampleprod.rpath.org@examplens:exampleprod-2, this would create a
    product subdirectory tree representing the contents of that product
    definition.

    Example: C{rbuild init example.rpath.org@ex:example-2}
    If your product does not use a standard label layout, or its product
    definition was not created through the rBuilder user interface, you
    will need to use the label to the product definition directly.
    """

    commands = ['init']
    paramHelp = ['<project shortname> <version>', '<label>']
    help = 'Create a directory for working with a product'

    def runCommand(self, handle, _, args):
        if len(args) == 3:
            label, = self.requireParameters(args, ['label'])[1:]
            self._initByLabelCommand(handle, label)
        else:
            params = self.requireParameters(args, ['product', 'version'])
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
        rb = self.handle.facade.rbuilder
        labelStr = rb.getProductLabelFromNameAndVersion(repository, version)
        return self.getProductVersionByLabel(labelStr)

    def getProductVersionByLabel(self, label):
        troveName = proddef.ProductDefinition.getTroveName() + ':source'
        version = self.handle.facade.conary._findTrove(
                                        troveName,
                                        str(label))[1]
        return str(version)

    def createProductDirectory(self, version, productDir=None):
        handle = self.handle
        if productDir is None:
            productDir = tempfile.mkdtemp(dir=os.getcwd())
            tempDir = productDir
        else:
            tempDir = None

        try:
            util.mkdirChain(productDir + '/.rbuild')
            os.mkdir(productDir + '/.rbuild/tracebacks', 0700)

            targetDir = productDir + '/.rbuild/product-definition'
            handle.facade.conary.checkout('product-definition', version,
                                          targetDir=targetDir)
            productStore = dirstore.CheckoutProductStore(handle, productDir)
            product = productStore.getProduct()
            if tempDir:
                productDir = '%s-%s' % (product.getProductShortname(),
                                        product.getProductVersion())
                if os.path.exists(productDir):
                    raise errors.PluginError(
                                    'Directory %r already exists.' % productDir)
                os.rename(tempDir, productDir)
                tempDir = None
                targetDir = productDir + '/.rbuild/product-definition'
        finally:
            if tempDir:
                util.rmtree(tempDir)

        logRoot = productDir + '/.rbuild'
        handle.ui.resetLogFile(logRoot)
        # This redundant log entry is the first entry in the new log,
        # corresponding to a similar entry in the toplevel log
        handle.ui._log('rBuild %s initialized %s-%s in %s',
            rbuild.constants.VERSION,
            product.getProductShortname(),
            product.getProductVersion(),
            productDir)

        stages = product.getStages()
        for stage in stages:
            stageDir = productDir + '/' + stage.name
            os.mkdir(stageDir)
            open(stageDir + '/.stage', 'w').write(stage.name + '\n')
            stageLabel = product.getLabelForStage(stage.name)
            open(stageDir + '/conaryrc', 'w').write(
                '# This file may be automatically overwritten by rbuild\n'
                'buildLabel %s\n'
                'installLabelPath %s\n' %(stageLabel, stageLabel))
        oldumask = os.umask(077)
        try:
            handle.getConfig().writeCheckoutFile(
                productDir + '/.rbuild/rbuildrc')
        finally:
            os.umask(oldumask)
        handle.ui.info('Created checkout for %s at %s', 
                        product.getProductDefinitionLabel(),
                        productDir)
        # get the versions that point to the real checkout now
        handle.productStore = dirstore.CheckoutProductStore(None, productDir)
        handle.product = handle.productStore.getProduct()
        return handle.productStore
