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
status command and related utilities.
"""
import os
import tempfile

from conary.lib import util

from rpath_common.proddef import api1 as proddef

from rbuild import errors
from rbuild import pluginapi
from rbuild.pluginapi import command

class StatusCommand(command.BaseCommand):
    """
    Prints status relative to the repository
    """

    commands = ['status']

    def runCommand(self, handle, _, args):
        if len(args) == 2:
            directory = handle.Product.getDefaultProductDirectory()
            if directory is None:
                raise errors.RbuildError('Could not find product from current directory')
            directories = [directory]
        else:
            directories = args[2:]

        for directory in directories:
            handle.Status.printDirectoryStatus(directory)


class Status(pluginapi.Plugin):
    name = 'status'

    def registerCommands(self):
        self.handle.Commands.registerCommand(StatusCommand)

    def printDirectoryStatus(self, dirName):
        '''
        Prints status of all source checkouts under a certain directory.
        @param dirName: Full path name of the directory to print
        '''
        dirName = os.path.abspath(dirName)
        productDir = self.handle.Product.getDefaultProductDirectory(dirName)
        if not productDir:
            raise errors.RbuildError('could not find product for directory %s',
                dirName)
        product = self.handle.Product.getProductStoreFromDirectory(productDir)
        self.printProductStatus(product)
        self._printOneDirectoryStatus(dirName)
        for dirpath, dirnames, _ in os.walk(dirName):
            for oneDir in dirnames:
                if oneDir == '.rbuild':
                    continue
                self._printOneDirectoryStatus(os.path.join(dirpath, oneDir))

    def _printOneDirectoryStatus(self, dirName):
        '''
        Prints directory status, if any, for a directory that is a
        checkout or stage.  For a directory that is neither a checkout
        not a stage, do nothing.
        @param dirName: Name of directory
        '''
        for statusLine in self._iterOneDirectoryStatus(dirName):
            print statusLine

    def _iterOneDirectoryStatus(self, dirName):
        '''
        Gets directory status, if any, for a directory that is a
        checkout or stage.  For a directory that is neither a checkout
        not a stage, do nothing.
        @param dirName: Name of directory
        '''
        if os.path.exists(os.sep.join((dirName, 'CONARY'))):
            yield dirName
            for x in self.handle.facade.conary.iterCheckoutLog(dirName,
                                                               newerOnly=True):
                yield x
            for x, y in self.handle.facade.conary.getCheckoutStatus(dirName):
                yield '%s   %s' %(x, y)
        if os.path.exists(os.sep.join((dirName, '.stage'))):
            yield 'Stage %s status:' %self.handle.Product.getStageName(dirName)

    def printProductStatus(self, product=None):
        '''
        Print current status of the product checkout.
        Currently, this is a list of commit log messages that are
        newer than the current checkout.
        '''
        if not product:
            product = self.handle.Product.getDefaultProductStore()
        for statusLine in self._iterProductStatus(product):
            print statusLine

    def _iterProductStatus(self, product):
        '''
        Essentially a specialized version of C{_iterOneDirectoryStatus}
        for the product checkout.  Does not call getCheckoutStatus
        because the product checkout is not expected to be used a a
        general storage space.
        '''
        for x in self.handle.facade.conary.iterCheckoutLog(
            product.getProductDefinitionDirectory(), newerOnly=True):
            yield x
