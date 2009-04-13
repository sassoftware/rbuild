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
Contains the functions which derive a package and commit the
resulting packages to the repository.
"""

import os

def derive(handle, troveToDerive):
    """
    Performs all the commands necessary to create a derived recipe.
    First it shadows the package, then it creates a checkout of the shadow
    and converts the checkout to a derived recipe package.

    @param handle: rbuild handle containing information about the
    active stage.
    @param troveToDerive: troveTuple of binary which we wish to derive
    @return: directory in which checkout was created
    """

    ui = handle.ui
    targetLabel = handle.productStore.getActiveStageLabel()
    targetDir = handle.productStore.getCheckoutDirectory(troveToDerive[0])
    troveName = troveToDerive[0]
    # displaying output along the screen allows there to be a record
    # of what operations were performed.  Since this command is
    # an aggregate of several commands I think that is appropriate,
    # rather than simply using a progress callback.
    ui.info('Shadowing %s=%s[%s] onto %s', troveToDerive[0],
                                           troveToDerive[1],
                                           troveToDerive[2],
                                           targetLabel)
    conaryFacade = handle.facade.conary

    conaryFacade.shadowSourceForBinary(troveToDerive[0],
                                       troveToDerive[1],
                                       troveToDerive[2],
                                       targetLabel)
    troveName = troveName.split(':')[0]
    conaryFacade.checkout(troveName, targetLabel, targetDir=targetDir)
    _writeDerivedRecipe(ui, conaryFacade, troveName, directory=troveName)

    extractDir = '%s/_ROOT_' %targetDir
    handle.ui.info('Extracting files from %s=%s[%s] into %s',
                   troveToDerive[0], troveToDerive[1], troveToDerive[2],
                   extractDir)
    troveName, version, flavor = troveToDerive
    conaryFacade.checkoutBinaryPackage(troveName, version, flavor,
            extractDir, tagScript='/dev/null')

    return targetDir

def _writeDerivedRecipe(ui, conaryFacade, troveName, directory):
    recipeName = troveName + '.recipe'
    recipePath = os.path.realpath(directory + '/' + recipeName)

    ui.info('Removing extra files from checkout')
    conaryFacade._removeNonRecipeFilesFromCheckout(recipePath)
    ui.info('Rewriting recipe file')
    recipeClass = conaryFacade._loadRecipeClassFromCheckout(recipePath)
    derivedRecipe = """
class %(className)s(DerivedPackageRecipe):
    name = '%(name)s'
    version = '%(version)s'

    def setup(r):
        '''
        In this recipe, you can make modifications to the package,
        starting with the contents of the parent (upstream) package.
        When this package is built, it starts with the contents
        of the parent package unpacked in %%(builddir)s, and you
        can modify those contents, deleting or modifying existing
        files.  You can also build new sources and add additional
        files to the package.

        Examples:

        # This appliance has high-memory-use PHP scripts
        r.Replace('memory_limit = 8M', 'memory_limit = 32M', '/etc/php.ini')

        # This appliance uses PHP as a command interpreter but does
        # not include a web server, so remove the file that creates
        # a dependency on the web server
        r.Remove('/etc/httpd/conf.d/php.conf')

        # This appliance requires that a few binaries be replaced
        # with binaries built from a custom archive that includes
        # a Makefile that honors the DESTDIR variable for its
        # install target.
        r.addArchive('foo.tar.gz')
        r.Make()
        r.MakeInstall()

        # This appliance requires an extra configuration file
        r.Create('/etc/myconfigfile', contents='some data')
        '''
""" % dict(className=recipeClass.__name__,
           name=recipeClass.name,
           version=recipeClass.version)
    open(recipePath, 'w').write(derivedRecipe)
