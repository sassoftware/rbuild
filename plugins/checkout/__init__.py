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
                     " an upstream version exists") }

    def addLocalParameters(self, argDef):
        argDef['derive'] = command.NO_PARAM
        argDef['shadow'] = command.NO_PARAM
        argDef['new']    = command.NO_PARAM

    def runCommand(self, handle, argSet, args):
        packageName, = self.requireParameters(args, ['packageName'])[1:]
        derive = argSet.pop('derive', False)
        new = argSet.pop('new', False)
        shadow = argSet.pop('shadow', False)
        self.runCheckoutCommand(handle, packageName, new=new, shadow=shadow,
                            derive=derive)

    def runCheckoutCommand(self, handle, packageName, new=False, shadow=False, 
                       derive=False):
        if [new, shadow, derive].count(True) > 1:
            raise errors.ParseError(
                'Only one of --new, --derive, or --shadow may be specified')
        if new:
            return handle.Checkout.newPackage(packageName)
        elif shadow:
            return handle.Checkout.shadowPackage(packageName)
        elif derive:
            return handle.Checkout.derivePackage(packageName)
        else:
            return handle.Checkout.checkoutPackageDefault(packageName)

class Checkout(pluginapi.Plugin):
    name = 'checkout'

    def registerCommands(self):
        self.handle.Commands.registerCommand(CheckoutCommand)

    def checkoutPackageDefault(self, packageName):
        existingPackage = self._getExistingPackage(packageName)
        if existingPackage:
            rc = self.checkoutPackage(packageName)
            self.handle.ui.info('Checked out existing package %r', packageName)
            return rc
        upstreamLatest = self._getUpstreamPackage(packageName)
        if upstreamLatest:
            raise errors.PluginError('\n'.join((
                    'The upstream source provides a version of this package.',
                    'Please specify:',
                    '  --shadow to shadow this package',
                    '  --derive to derive from it',
                    '  --new to replace it with a new version')))
        self.newPackage(packageName)


    def checkoutPackage(self, packageName):
        currentLabel = self.handle.productStore.getActiveStageLabel()
        self.handle.facade.conary.checkout(packageName, currentLabel)
        return True

    def derivePackage(self, packageName):
        upstreamLatest = self._getUpstreamPackage(packageName)
        if not upstreamLatest:
            raise errors.PluginError(
                        'cannot derive %s: no upstream binary' % packageName)
        derive.derive(self.handle, upstreamLatest)
        self.handle.ui.info('Derived %s from %s=%s[%s].', packageName, *upstreamLatest)
        self.handle.ui.info(
                'Edit recipe to add changes your changes to the binary package')

    def shadowPackage(self, packageName):
        origName, version, flavor = self.handle.facade.conary.parseTroveSpec(packageName)
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
                raise errors.PluginError(
                        'cannot shadow %s: no upstream binary' % packageName)

        name, version, flavor = package            

        currentLabel = self.handle.productStore.getActiveStageLabel()
        self.handle.facade.conary.shadowSourceForBinary(name, version, flavor,
                                                        currentLabel)
        self.checkoutPackage(origName)
        self.handle.ui.info('Shadowed package %r', packageName)

    def newPackage(self, packageName):
        existingPackage = self._getExistingPackage(packageName)
        if existingPackage:
            raise errors.PluginError('\n'.join((
                'This package already exists in the product.',
                'Use "rbuild checkout %s" to checkout the existing package, '
                'or give the new package a different name.' % \
                packageName)))

        upstreamLatest = self._getUpstreamPackage(packageName)
        if upstreamLatest:
            self.handle.ui.warning('Replacing upstream package %s.' % \
                packageName)

        currentLabel = self.handle.productStore.getActiveStageLabel()
        self.handle.facade.conary.createNewPackage(
                                            packageName, currentLabel)
        self.handle.ui.info('Created new package %r', packageName)
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
        currentLabel = self.handle.productStore.getActiveStageLabel()
        return self.handle.facade.conary._findTrove(packageName + ':source',
                                                    currentLabel,
                                                    allowMissing=True)

    def _getRemotePackage(self, packageName, label):
        troveTup = self.handle.facade.conary._findTrove(packageName + ':source',
                                                        label, 
                                                        allowMissing=True)
        return troveTup
