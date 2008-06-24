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

from rbuild import errors
from rbuild import pluginapi
from rbuild.pluginapi import command

from rbuild_plugins.checkout import derive

#TODO: separate out determining what checkout to get from actually creating
# that checkout to allow for other interfaces

class CheckoutCommand(command.BaseCommand):
    """
    Creates a checkout of the package, creating a new package if necessary.

    If an upstream version of the package is available, then the user must
    specify whether the upstream version should be shadowed, derived, or
    a new package should be created.
    """
    commands = ['checkout']
    docs = {'derive' : "Create a derived package based on an upstream one",
            'shadow' : "Create a shadowed package based on an upstream one",
            'new' : ("Create a new version of the package regardless of"
                     " whether an upstream one exists") }

    def addParameters(self, argDef):
        command.BaseCommand.addParameters(self, argDef)
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
            raise errors.RbuildError('\n'.join((
                    'The upstream source provides a version of this package.',
                    'Please specify:',
                    '  --shadow to shadow this package',
                    '  --derive to derive from it',
                    '  --new to replace it with a new version')))
        self.newPackage(packageName)


    def checkoutPackage(self, packageName):
        currentLabel = self.handle.getProductStore().getActiveStageLabel()
        self.handle.facade.conary.checkout(packageName, currentLabel)
        return True

    def derivePackage(self, packageName):
        upstreamLatest = self._getUpstreamPackage(packageName)
        if not upstreamLatest:
            raise errors.RbuildError(
                        'cannot derive %s: no upstream binary' % packageName)
        derive.derive(self.handle, upstreamLatest)
        self.handle.ui.info('Derived %s from %s=%s[%s].', packageName, *upstreamLatest)
        self.handle.ui.info(
                'Edit recipe to add changes your changes to the binary package')

    def shadowPackage(self, packageName):
        upstreamLatest = self._getUpstreamPackage(packageName)
        if not upstreamLatest:
            raise errors.RbuildError(
                        'cannot shadow %s: no upstream binary' % packageName)
        name, version, flavor = upstreamLatest
        currentLabel = self.handle.getProductStore().getActiveStageLabel()
        self.handle.facade.conary.shadowSourceForBinary(name, version, flavor,
                                                        currentLabel)
        self.checkoutPackage(packageName)
        self.handle.ui.info('Shadowed package %r', packageName)

    def newPackage(self, packageName):
        currentLabel = self.handle.getProductStore().getActiveStageLabel()
        self.handle.facade.conary.createNewPackage(
                                            packageName, currentLabel)
        self.handle.ui.info('Created new package %r', packageName)
        return


    def _getUpstreamPackage(self, packageName):
        product = self.handle.getProductStore().get()
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
        currentLabel = self.handle.getProductStore().getActiveStageLabel()
        return self.handle.facade.conary._findTrove(packageName + ':source',
                                                    currentLabel,
                                                    allowMissing=True)
