#
# Copyright (c) 2008-2009 rPath, Inc.
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

from rbuild import errors
from rbuild import pluginapi
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
            'template' : "If creating a new package, specify a template."}

    def addLocalParameters(self, argDef):
        argDef['derive'] = command.NO_PARAM
        argDef['shadow'] = command.NO_PARAM
        argDef['new']    = command.NO_PARAM
        argDef['template']    = command.ONE_PARAM

    def runCommand(self, handle, argSet, args):
        packageName, = self.requireParameters(args, ['packageName'])[1:]
        derive = argSet.pop('derive', False)
        new = argSet.pop('new', False)
        shadow = argSet.pop('shadow', False)
        template = argSet.pop('template', None)
        self.runCheckoutCommand(handle, packageName, new=new, shadow=shadow,
                            derive=derive, template=template)

    def runCheckoutCommand(self, handle, packageName, new=False, shadow=False,
                           derive=False, template=None):
        if [new, shadow, derive].count(True) > 1:
            raise errors.ParseError(
                'Only one of --new, --derive, or --shadow may be specified')
        if new:
            return handle.Checkout.newPackage(packageName, template=template)
        elif shadow:
            return handle.Checkout.shadowPackage(packageName)
        elif derive:
            return handle.Checkout.derivePackage(packageName)
        else:
            return handle.Checkout.checkoutPackageDefault(packageName,
                                                          template=template)

class Checkout(pluginapi.Plugin):
    name = 'checkout'

    def registerCommands(self):
        self.handle.Commands.registerCommand(CheckoutCommand)

    def checkoutPackageDefault(self, packageName, template=None):
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
        self.newPackage(packageName, template=template)


    def checkoutPackage(self, packageName):
        productStore = self.handle.productStore
        currentLabel = productStore.getActiveStageLabel()
        targetDir = productStore.getCheckoutDirectory(packageName)
        self.handle.facade.conary.checkout(
            packageName, currentLabel, targetDir=targetDir)
        return targetDir

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

    def newPackage(self, packageName, message=None, template=None):
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

            conaryFacade.createNewPackage(packageName, currentLabel,
                                          targetDir=targetDir,
                                          template=template)
            ui.info('Created new package %r in %r', packageName,
                self._relPath(os.getcwd(), targetDir))
        return

    def _getUpstreamPackage(self, packageName):
        product = self.handle.product
        upstreamSources = product.getSearchPaths()
        upstreamSources = [(x.troveName, x.label, None)
                            for x in upstreamSources]
        troveList =  self.handle.facade.conary._findPackageInGroups(
                         upstreamSources,
                         packageName)
        if troveList:
            # FIXME: this could be multiple packages.  We need a good
            # way to select between them
            return troveList[0]
        return None

    def _getExistingPackage(self, packageName):
        if not self.handle.productStore:
            # Neither new nor checkout functions outside of a product store
            raise errors.PluginError(
                'Current directory is not part of a product.\n'
                'To initialize a new product directory, use "rbuild init"')
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
