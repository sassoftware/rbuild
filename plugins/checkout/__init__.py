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


"""
Checkout command and related utilities.
"""
import os
import tempfile

from conary.lib import util

from rbuild import errors
from rbuild import pluginapi
from rbuild.decorators import requiresStage
from rbuild.pluginapi import command

from rbuild_plugins.checkout import derive

#TODO: separate out determining what checkout to get from actually creating
# that checkout to allow for other interfaces

class CheckoutCommand(command.BaseCommand):
    """
    Check out a package, creating a new package if necessary.

    If the product's platform contains a package by the same name,
    then you must specify whether to shadow or derive from that
    upstream version, or to create a new package by the same name
    that is not related to the upstream version.

    A derived package starts with the contents of the binary
    package from the platform, generally used to make modifications
    that do not require rebuilding binaries.

    A shadow allows you to make changes relative to the platform's
    source package, changing how the package is built, and requiring
    rebuilding binaries.
    """
    help = 'Check out packages and groups for editing'
    paramHelp = '[<options>] <packagename>'

    commands = ['checkout']
    docs = {'derive' : "Create derived package (based on upstream binary)",
            'shadow' : "Create shadowed package (based on upstream source)",
            'new' : ("Create a new version of the package even if"
                     " an upstream version exists"), 
            'factory' : ("If creating a new package, specify its factory"
                         " (not needed when creating a factory package)."),
            'template' : "If creating a new package, specify a template."}

    def addLocalParameters(self, argDef):
        argDef['derive'] = command.NO_PARAM
        argDef['shadow'] = command.NO_PARAM
        argDef['new']    = command.NO_PARAM
        argDef['factory']     = command.OPT_PARAM
        argDef['template']    = command.ONE_PARAM

    def runCommand(self, handle, argSet, args):
        packageName, = self.requireParameters(args, ['packageName'])[1:]
        derive = argSet.pop('derive', False)
        new = argSet.pop('new', False)
        shadow = argSet.pop('shadow', False)
        template = argSet.pop('template', None)
        factory = argSet.pop('factory', None)
        self.runCheckoutCommand(handle, packageName, new=new, shadow=shadow,
                            derive=derive, template=template,
                            factory=factory)

    def runCheckoutCommand(self, handle, packageName, new=False, shadow=False,
                           derive=False, template=None, factory=None):
        if [new, shadow, derive].count(True) > 1:
            raise errors.ParseError(
                'Only one of --new, --derive, or --shadow may be specified')
        if new:
            return handle.Checkout.newPackage(packageName, template=template,
                factory=factory)
        elif shadow:
            return handle.Checkout.shadowPackage(packageName)
        elif derive:
            return handle.Checkout.derivePackage(packageName)
        else:
            return handle.Checkout.checkoutPackageDefault(packageName,
                                                          template=template,
                                                          factory=factory)

class Checkout(pluginapi.Plugin):
    name = 'checkout'

    def registerCommands(self):
        self.handle.Commands.registerCommand(CheckoutCommand)

    @requiresStage
    def checkoutPackageDefault(self, packageName, template=None,
                               factory=None):
        existingPackage = self._getExistingPackage(packageName)
        if existingPackage:
            targetDir = self.checkoutPackage(packageName)
            self.handle.ui.info('Checked out existing package %r in %r',
                packageName, self._relPath(os.getcwd(), targetDir))
            return targetDir

        upstreamLatest = self._getUpstreamPackage(packageName)
        if upstreamLatest:
            raise errors.PluginError('\n'.join((
                    'The upstream source provides a version of this package.',
                    'Please specify:',
                    '  --shadow to shadow this package',
                    '  --derive to derive from it',
                    '  --new to replace it with a new version')))
        self.newPackage(packageName, template=template, factory=factory)

    @requiresStage
    def checkoutPackage(self, packageName):
        productStore = self.handle.productStore
        currentLabel = productStore.getActiveStageLabel()
        targetDir = productStore.getCheckoutDirectory(packageName)
        self.handle.facade.conary.checkout(
            packageName, currentLabel, targetDir=targetDir)
        return targetDir

    @requiresStage
    def derivePackage(self, packageName):
        ui = self.handle.ui
        upstreamLatest = self._getUpstreamPackage(packageName)
        if not upstreamLatest:
            raise errors.PluginError(
                        'cannot derive %s: no upstream binary' % packageName)
        targetDir = derive.derive(self.handle, upstreamLatest)
        ui.info('Derived %r in %r from %s=%s[%s]',
            packageName, targetDir, *upstreamLatest)
        ui.info('Edit the recipe to add your changes to the binary package.')

    @requiresStage
    def shadowPackage(self, packageName):
        conaryFacade = self.handle.facade.conary
        productStore = self.handle.productStore
        origName, version, flavor = conaryFacade.parseTroveSpec(packageName)
        package = None

        if version:
            package = self._getRemotePackage(origName, version)
            if package is None:
                raise errors.PluginError(
                        '%s:source does not exist on label %s.' % \
                        (origName, version))
        else:
            package = self._getUpstreamPackage(packageName)
            if package is None:
                # FIXME: since we shadow only source, why care about binary?
                raise errors.PluginError(
                        'cannot shadow %s: no upstream binary' % packageName)

        name, version, flavor = package            

        currentLabel = productStore.getActiveStageLabel()
        conaryFacade.shadowSourceForBinary(name, version, flavor,
                                                        currentLabel)
        targetDir = self.checkoutPackage(origName)
        self.handle.ui.info('Shadowed package %r in %r', packageName,
                self._relPath(os.getcwd(), targetDir))

    @requiresStage
    def newPackage(self, packageName, message=None, template=None,
                   factory=None):
        ui = self.handle.ui
        conaryFacade = self.handle.facade.conary
        productStore = self.handle.productStore
        currentLabel = productStore.getActiveStageLabel()
        targetDir = productStore.getCheckoutDirectory(packageName)
        existingPackage = self._getExistingPackage(packageName)

        if existingPackage:
            if existingPackage[1].isShadow(): 
                confirmDetach = ui.getYn(
                    '%s is shadowed on the current label.\n'
                    'Do you want to detach this package from its '
                    'parent? (Y/N): '  % packageName )
                if not confirmDetach:
                    return
                conaryFacade.detachPackage(
                    existingPackage, '/' + currentLabel, message)
                ui.info('Detached package %s from its parent.' \
                    % packageName)
            else:                    
                raise errors.PluginError('\n'.join((
                    'This package already exists in the product.',
                    'Use "rbuild checkout %s" to checkout the existing '
                    'package to modify its files, or give the new package '
                    'a different name.' % packageName)))
        else:
            upstreamLatest = self._getUpstreamPackage(packageName)
            if upstreamLatest:
                ui.warning('Package %s exists upstream.' %packageName)
                confirmReplace = ui.getYn(
                    'Do you want to replace the upstream version? (Y/N):')
                if not confirmReplace:
                    return

            if packageName.startswith('factory-'):
                # A package named 'factory-' is required to BE a factory
                factory = 'factory'

            conaryFacade.createNewPackage(packageName, currentLabel,
                                          targetDir=targetDir,
                                          template=template,
                                          factory=factory)

            ui.info('Created new package %r in %r', packageName,
                self._relPath(os.getcwd(), targetDir))
        return

    def _getUpstreamPackage(self, packageName):
        product = self.handle.product
        upstreamSources = product.getSearchPaths()
        upstreamSources = [(x.troveName, x.label, None)
                            for x in upstreamSources]
        troveList = self.handle.facade.conary._findPackageInSearchPaths(
                         upstreamSources,
                         packageName)
        if troveList:
            # FIXME: this could be multiple packages.  We need a good
            # way to select between them
            return troveList[0]
        return None

    def _getExistingPackage(self, packageName):
        currentLabel = self.handle.productStore.getActiveStageLabel()
        return self.handle.facade.conary._findTrove(packageName + ':source',
                                                    currentLabel,
                                                    allowMissing=True)

    def _getRemotePackage(self, packageName, label):
        if not packageName.endswith(':source'):
            packageName = packageName + ':source'
        troveTup = self.handle.facade.conary._findTrove(packageName,
                                                        label, 
                                                        allowMissing=True)
        return troveTup

    @staticmethod
    def _relPath(fromPath, toPath):
        """
        Print the relative path from directory fromPath to directory toPath
        If C{fromPath} is from C{os.getcwd()} then the output of this
        command should be a relative path that would be appropriate for
        the cd command, because this function is used to display paths
        to the user that would be used for this purpose.
        @param fromPath: directory name from which to construct a
        relative symlink
        @param toPath: directory name to which to construct a relative
        symlink
        @return: relative symlink from fromPath to toPath
        """
        # Note that abspath also normalizes
        absFromPath = os.path.abspath(fromPath)
        absToPath = os.path.abspath(toPath)
        if absFromPath == absToPath:
            # identical paths
            return '.'
        fromPathList = absFromPath.split('/')
        toPathList = absToPath.split('/')
        while fromPathList and toPathList and fromPathList[0] == toPathList[0]:
            fromPathList.pop(0)
            toPathList.pop(0)

        upDots = '/'.join((len(fromPathList) * [".."])) or '.'
        downDirs = '/'.join(toPathList)
        if downDirs:
            downDirs = '/' + downDirs
        return upDots + downDirs
