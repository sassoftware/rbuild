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

from rbuild_plugins.edit import derive

#TODO: separate out determining what checkout to get from actually creating
# that checkout to allow for other interfaces

class EditCommand(command.BaseCommand):
    commands = ['edit']

    def runCommand(self, handle, argSet, args):
        packageName, = self.requireParameters(args, ['packageName'])[1:]
        derive = argSet.pop('derive', False)
        new = argSet.pop('new', False)
        shadow = argSet.pop('shadow', False)
        self.runEditCommand(handle, packageName, new=new, shadow=shadow,
                            derive=derive)

    def runEditCommand(self, handle, packageName, new=False, shadow=False, 
                       derive=False):
        if [new, shadow, derive].count(True) > 1:
            raise errors.ParseError(
                'Only one of new, derive, or shadow may be specified')
        if new:
            return handle.Edit.newPackage(packageName)
        elif shadow:
            return handle.Edit.shadowPackage(packageName)
        elif derive:
            return handle.Edit.derivePackage(packageName)
        else:
            return handle.Edit.editPackage(packageName)

class Edit(pluginapi.Plugin):
    name = 'edit'

    def registerCommands(self):
        self.handle.Commands.registerCommand(EditCommand)

    def editPackage(self, packageName):
        existingPackage = self._getExistingPackage(packageName)
        if existingPackage:
            return self.checkoutPackage(packageName)
        upstreamLatest = self._getUpstreamPackage(packageName)
        if upstreamLatest:
            raise errors.RbuildError('An upstream version of this package'
                                     ' exists.  Please specify whether you'
                                     ' would like to shadow this package,'
                                     ' derive from it, or replace it with'
                                     ' a new version')
        self.newPackage(packageName)


    def checkoutPackage(self, packageName):
        self.handle.facade.conary.checkout(packageName)
        return True

    def derivePackage(self, packageName):
        upstreamLatest = self._getUpstreamPackage(packageName)
        if not upstreamLatest:
            raise errors.RbuildError(
                        'cannot derive %s: no upstream binary' % packageName)
        derive.derive(self.handle, upstreamLatest)

    def shadowPackage(self, packageName):
        upstreamLatest = self._getUpstreamPackage(packageName)
        if not upstreamLatest:
            raise errors.RbuildError(
                        'cannot shadow %s: no upstream binary' % packageName)
        name, version = upstreamLatest[0:2]
        self.handle.facade.conary.shadowSource(name, version.branch())

    def newPackage(self, packageName):
        currentLabel = self.handle.getProductStore().getActiveLabel()
        self.handle.facade.conary.createNewPackage(
                                            packageName, currentLabel)
        return


    def _getUpstreamPackage(self, packageName):
        product = self.handle.getProductStore().get()
        troveList =  self.handle.facade.conary._findPackageInGroups(
                         product.getUpstreamSources(),
                         packageName)
        if troveList:
            # FIXME: this could be multiple packages.  We need a good
            # way to select between them
            return troveList[0]
        return None

    def _getExistingPackage(self, packageName):
        currentLabel = self.handle.getProductStore().getActiveStageLabel()
        return self.handle.facade.conary._findTrove(packageName + ':source',
                                                    currentLabel)
