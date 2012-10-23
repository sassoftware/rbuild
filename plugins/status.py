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
status command and related utilities.
"""
import os

from rbuild import pluginapi
from rbuild.pluginapi import command

from rbuild.productstore import dirstore

CONCISE, DEFAULT, VERBOSE = (1, 2, 3)

class StatusCommand(command.BaseCommand):
    """
    Prints summary of differences between the local checkout and
    the repository.  New B{l}ocal changes that have not been committed
    to the repository are marked with a leading C{L} character; 
    New changes that have been committed to the B{r}epository but
    not yet applied to the local checkout are marked with a leading
    C{R] character.  If the C{--concise} options is specified, prints
    a one-line summary for each Conary source component directory
    checkout.  If the C{--concise} option is not specified,
    then all commit messages for versions in the repository that
    are newer than the latest local update are printed, and a
    one-line-per-file summary of changes made locally but not yet
    committed is printed.  If the C{--verbose}} option is specified,
    differences within files are printed, again both for newer
    changes in the repository and for local changes not yet
    committed to the repository.
    """

    commands = ['status']
    help = 'Print summary of differences between filesystem and repository'
    docs = {
        'all' : 'Print status for entire product checkout',
        'product' : 'Print status for the product definition',
        'no-product' : 'Do not print status for the product definition',
        'concise' : 'Print one-line summary for each checkout',
        'local' : 'Print out only local changes not committed',
        'repository' :
            'Print out only changes in repository not applied locally',
    }

    def addLocalParameters(self, argDef):
        argDef['all'] = command.NO_PARAM
        argDef['product'] = command.NO_PARAM
        argDef['no-product'] = command.NO_PARAM
        argDef['concise'] = command.NO_PARAM
        argDef['local'] = command.NO_PARAM
        argDef['repository'] = command.NO_PARAM

    def runCommand(self, handle, argSet, args):
        args = args[2:]
        allArg = argSet.pop('all', False)

        conciseArg = argSet.pop('concise', False)
        verboseArg = argSet.pop('verbose', False)
        # --verbose overrides --concise; can't be both
        if verboseArg:
            verbosity = VERBOSE
        elif conciseArg:
            verbosity = CONCISE
        else:
            verbosity = DEFAULT

        repositoryArg = argSet.pop('repository', False)
        localArg = argSet.pop('local', False)
        if not localArg and not repositoryArg:
            # neither == both
            localArg = repositoryArg = True

        cwd = os.getcwd()
        dirList = args
        if allArg:
            dirList = [dirstore.getDefaultProductDirectory(
                dirName=cwd, error=True)]
        elif not args:
            dirList = [cwd]

        # productArg = True => print product-definition status
        # default not to print if in a checkout, otherwise do
        productArg = not handle.facade.conary.isConaryCheckoutDirectory(cwd)
        # --product overrides --no-product
        productArg = not argSet.pop('no-product', not productArg)
        productArg = argSet.pop('product', productArg)

        for thisDir in dirList:
            handle.Status.printDirectoryStatus(thisDir, verbosity=verbosity,
                product=productArg, local=localArg, repository=repositoryArg)



class Status(pluginapi.Plugin):
    name = 'status'

    def registerCommands(self):
        self.handle.Commands.registerCommand(StatusCommand)

    def printDirectoryStatus(self, directory, verbosity=DEFAULT, product=False,
            local=True, repository=True):
        #pylint: disable-msg=R0913,R0914
        # conflating arguments would just make this harder to understand
        # not amenable to refactoring to split up local variables
        '''
        Prints status of various things based on the current
        working directory.  The default output displays what
        packages and files have changed, but not the contents
        of the changes to the files.
        @param directory: name of directory to print status of
        @param verbosity: level of change to display
        @param product: Display changes to product similar to packages
        @param local: Display local filesystem changes not yet committed
        @param repository: Display changes committed to the repository
        but not yet applied locally

        At least one of C{local} and C{repository} must be set.
        '''

        if not local and not repository:
            raise ValueError(
                'At least one of local and repository must be True')

        productStore = dirstore.CheckoutProductStore(self.handle, directory)
        proddefDir = productStore.getProductDefinitionDirectory()
        if product:
            self._printOneDirectoryStatus(
                proddefDir, 'Product Definition', verbosity, proddef=True,
                local=local, repository=repository)

        baseDir = productStore.getBaseDirectory()
        baseDirLen = len(baseDir)
        def stripPrefix(dirName):
            # Get the name relative to the checkout, not the current
            # working directory.  This is like most version control
            # systems -- see "hg stat" for one of many examples
            if dirName == baseDir:
                # no empty baseDir
                return baseDir
            if dirName.startswith(baseDir):
                # make relative to baseDir
                return dirName[baseDirLen+1:]
            return dirName

        pendingAnnounce = self._printOneDirectoryStatus(
            directory, stripPrefix(directory), verbosity, '',
            local=local, repository=repository)

        for dirpath, dirnames, _ in os.walk(directory):
            for oneDir in sorted(dirnames):
                if oneDir == '.rbuild':
                    # product store already handled separately if
                    # appropriate, stop from recursing
                    dirnames.remove('.rbuild')
                    continue
                dirName = os.path.join(dirpath, oneDir)
                pendingAnnounce = self._printOneDirectoryStatus(
                    dirName, stripPrefix(dirName), verbosity, pendingAnnounce,
                    local=local, repository=repository)


    def _printOneDirectoryStatus(self, dirName, displayName,
            verbosity, pendingAnnounce=None, proddef=False,
            local=True, repository=True):
        #pylint: disable-msg=R0912,R0913,R0914
        # branches are required by spec
        # conflating arguments would just make this harder to understand
        # not amenable to refactoring to split up local variables
        '''
        Prints directory status, if any, for a directory that is a
        checkout or stage.  For a directory that is neither a checkout
        not a stage, do nothing.
        @param dirName: Path to directory
        @param displayName: Name to display
        @param verbosity: Level of verbosity
        @param pendingAnnounce: Stage name not yet announced
        @param proddef: Whether this is the product definition
        @param local: Display local filesystem changes not yet committed
        @param repository: Display changes committed to the repository
        but not yet applied locally
        @return: current stage name pendingAnnounce for next iteration
        '''

        conaryfacade = self.handle.facade.conary
        if conaryfacade.isConaryCheckoutDirectory(dirName):
            ui = self.handle.ui

            repositoryChanges = False
            if repository:
                newerVersions = [x for x in
                    conaryfacade._getNewerRepositoryVersions(dirName)]
                repositoryChanges = newerVersions and True or False

            localChanges = False
            if local:
                status = conaryfacade.getCheckoutStatus(dirName)
                if status:
                    localChanges = True

            def writeHeader(header):
                ui.write('%s\n%s', header, '='*len(header))
                
            thisStage = dirstore.getStageNameFromDirectory(dirName)
            if localChanges or repositoryChanges:
                if pendingAnnounce is not None and pendingAnnounce != thisStage:
                    ui.write('\n')
                    writeHeader('%s stage status:' %thisStage)
                    pendingAnnounce = thisStage
                elif proddef:
                    writeHeader('Product %s-%s status:' %(
                                self.handle.product.getProductName(),
                                self.handle.product.getProductVersion()))

                ui.write('%s%s  %s', localChanges and 'L' or '-',
                                     repositoryChanges and 'R' or '-',
                                     displayName)
                
                if verbosity >= DEFAULT:
                    if localChanges and status:
                        ui.write('  * Local changes not committed'
                                    ' to repository:')
                        for x, y in status:
                            ui.write('L-  %s   %s/%s' % (x, displayName, y))
                        if verbosity >= VERBOSE:
                            for line in conaryfacade.iterCheckoutDiff(dirName):
                                ui.write(line)
                    if repositoryChanges:
                        ui.write('  * Remote repository commit messages'
                                    ' for newer versions:')
                        for line in conaryfacade.getCheckoutLog(
                                dirName, versionList=newerVersions):
                            ui.write('-R  %s', line)
                        if verbosity >= VERBOSE:
                            for line in conaryfacade.iterRepositoryDiff(
                                dirName, newerVersions[-1]):
                                ui.write(line)

        return pendingAnnounce
