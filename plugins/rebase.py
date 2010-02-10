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
rebase command and related utilities.
"""
import os

from rpath_common.proddef import api1 as proddef

from rbuild.pluginapi import command
from rbuild import pluginapi

from rbuild import errors

class ModifiedFilesError(errors.PluginError):
    template = ('Modifed files %(filenames)r exist in product checkout'
                ' directory %(dirname)r')
    params = ['filenames', 'dirname']

class FileConflictsError(errors.PluginError):
    template = ('Failed merge files %(filenames)r exist in product checkout'
                ' directory %(dirname)r')
    params = ['filenames', 'dirname']

class IncompatibleProductDefinitionError(errors.PluginError):
    template = ('Can not rebase because the rBuilder where this product resides'
                ' does not support the same product definition schema version '
                'as the local install.')
    params = []

class OlderProductDefinitionError(IncompatibleProductDefinitionError):
    template = (IncompatibleProductDefinitionError.template + ' To Resolve this'
                ' error please update rpath-product-definition. You may also '
                'rebase through the rBuilder user interface.')

class RebaseCommand(command.BaseCommand):
    help = 'Update product to most recent platform version'

    commands = ['rebase']

    def runCommand(self, handle, _, args):
        #disallow extra parameters
        _, extra = self.requireParameters(args, allowExtra=True, maxExtra=1)
        if extra:
            label = extra[0]
        else:
            label = None
        handle.Rebase.rebaseProduct(label)

class Rebase(pluginapi.Plugin):
    name = 'rebase'

    def registerCommands(self):
        self.handle.Commands.registerCommand(RebaseCommand)

    def rebaseProduct(self, label=None):
        handle = self.handle
        ui = handle.ui

        # default to 2.0 if using rpath-product-definition 4.0 or earlier;
        # the last schema version that is widely compatible at this time.
        # After rpath-product-definition 4.0 is fully retired, the check
        # for preMigrateVersion and not passing version= to saveToRepository
        # can be removed, simplifying this code
        schemaVer = '2.0'
        versionKw = {}
        if hasattr(handle.product, 'preMigrateVersion'):
            schemaVer = handle.product.preMigrateVersion
            versionKw['version'] = None

        rbSchemaVer = self._getrBuilderProductDefinitionSchemaVersion(schemaVer)
        if 'version' in versionKw:
            versionKw['version'] = rbSchemaVer

        proddir = handle.productStore.getProductDefinitionDirectory()
        conaryClient = handle.facade.conary._getConaryClient()
        self._raiseErrorIfModified(proddir)
        self._raiseErrorIfConflicts(proddir)
        # update to latest upstream to avoid regressions (RBLD-155)
        handle.productStore.update()
        self._raiseErrorIfConflicts(proddir)
        oldPlatformSource = handle.product.getPlatformSourceTrove()
        handle.product.rebase(conaryClient, label=label)
        self._raiseErrorIfConflicts(proddir)
        handle.product.saveToRepository(conaryClient, **versionKw)
        handle.productStore.update()
        platformSource = handle.product.getPlatformSourceTrove()
        def trailingVersionDifference(a, b):
            a = a.split('/')
            b = b.split('/')
            for i in range(len(b)):
                if a[i] != b[i]:
                    return '/'.join(b[i:])
        if oldPlatformSource != platformSource:
            ui.info(
                'Updated from %s to latest %s' % (oldPlatformSource,
                    trailingVersionDifference(oldPlatformSource,
                                              platformSource,)))

    def _getrBuilderProductDefinitionSchemaVersion(self, schemaVer):
        '''
        Get the rBuilder product definition schema versions, raising
        an error if the schema version is incompatible with the
        existing schema version.
        '''
        rbuilder = self.handle.facade.rbuilder
        currentMaxSchemaVersion = proddef.ProductDefinition.version
        rbuilderSchemaVersion = rbuilder.getProductDefinitionSchemaVersion()

        # schema versions should always be integers separated by dots,
        # which compare correctly with < and >

        # we do not need to test if we aren't changing the schema version
        # because presumably the decision was already made (RBLD-297)
        if schemaVer < '2.0' or schemaVer != rbuilderSchemaVersion:
            if rbuilderSchemaVersion > currentMaxSchemaVersion:
                raise OlderProductDefinitionError

        return rbuilderSchemaVersion

    def _raiseErrorIfModified(self, proddir):
        '''
        Enforce preconditions for safe rebasing: no files in checkout modified
        @param proddir: path to product checkout directory
        '''
        modifiedFiles = self._modifiedFileNames(proddir)
        if modifiedFiles:
            raise ModifiedFilesError(filenames=', '.join(modifiedFiles),
                                     dirname=proddir)

    def _raiseErrorIfConflicts(self, proddir):
        '''
        Enforce preconditions for safe rebasing: no .conflicts files exist
        @param proddir: path to product checkout directory
        '''
        conflictFiles = self._fileConflictNames(proddir)
        if conflictFiles:
            raise FileConflictsError(filenames=', '.join(conflictFiles),
                                     dirname=proddir)

    def _modifiedFileNames(self, checkoutDirectory):
        '''
        Report any modified files in a checkout
        @param checkoutDirectory: path to directory to test
        '''
        conaryfacade = self.handle.facade.conary
        return [x[1] for x in conaryfacade.getCheckoutStatus(checkoutDirectory)
                if x[0] == 'M']

    def _fileConflictNames(self, checkoutDirectory):
        '''
        Tests whether .conflicts files exist in a checkout
        @param checkoutDirectory: path to directory to test
        '''
        return [x for x in os.listdir(checkoutDirectory)
                if x.endswith('.conflicts')]
