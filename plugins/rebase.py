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
rebase command and related utilities.
"""
import os

from rpath_proddef import api1 as proddef

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

def _trailingVersionDifference(a, b):
    if not a:
        return b
    a = a.split('/')
    b = b.split('/')
    for i in range(len(b)):
        if a[i] != b[i]:
            return '/'.join(b[i:])

def _formatSearchPath(searchPath):
    return [str('%s=%s/%s' %(x.troveName, x.label, x.version))
            for x in searchPath]


class RebaseCommand(command.BaseCommand):
    """
    Modifies the version of the upstream platform and platform
    definition currently in use.  In normal use, updates to the
    latest version of the platform definition and the latest
    version of each of the search path elements specified in
    the platform definition.  Alternatively, can be used to
    change the upstream platform used by providing the label
    for the platform definition for the new upstream platform.
    After such a change all packages normally must be rebuilt.
    """

    help = 'Update product to most recent platform version'
    paramHelp = '[label]'
    docs = {
        'interactive' : 'Allow user to choose whether to apply changes',
        'test' : 'Show what changes would be applied, but do not apply them',
    }

    commands = ['rebase']

    def addLocalParameters(self, argDef):
        argDef['interactive'] = command.NO_PARAM
        argDef['test'] = command.NO_PARAM

    def runCommand(self, handle, argSet, args):
        interactive = argSet.pop('interactive', False)
        test = argSet.pop('test', False)
        #disallow extra parameters
        _, extra = self.requireParameters(args, allowExtra=True, maxExtra=1)
        if extra:
            label = extra[0]
        else:
            label = None
        handle.Rebase.rebaseProduct(label=label,
            interactive=interactive, test=test)

class Rebase(pluginapi.Plugin):
    name = 'rebase'

    def registerCommands(self):
        self.handle.Commands.registerCommand(RebaseCommand)

    def rebaseProduct(self, label=None, interactive=False, test=False):
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
        oldSearchPaths = handle.product.getSearchPaths()
        handle.product.rebase(conaryClient, label=label)
        platformSource = handle.product.getPlatformSourceTrove()
        searchPaths = handle.product.getSearchPaths()
        oldFormattedSP = _formatSearchPath(oldSearchPaths)
        formattedSP = _formatSearchPath(searchPaths)
        if oldFormattedSP != formattedSP:
            ui.info('Update search path from:\n%s\nto:\n%s',
                '\n'.join(['    %s' %x for x in oldFormattedSP]),
                '\n'.join(['    %s' %x for x in formattedSP]))
        if oldPlatformSource != platformSource:
            ui.info('Update %s -> %s',
                    oldPlatformSource,
                    _trailingVersionDifference(oldPlatformSource,
                                               platformSource,))
        if test:
            return

        if interactive:
            if not ui.getYn('Commit these changes? (Y/n)', default=True):
                return

        handle.product.saveToRepository(conaryClient, **versionKw)
        handle.productStore.update()

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
