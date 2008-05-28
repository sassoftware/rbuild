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

from conary.lib import log

def derive(handle, troveToDerive):
    """
        Performs all the commands necessary to create a derived recipe.
        First it shadows the package, then it creates a checkout of the shadow
        and converts the checkout to a derived recipe package.

        @param handle: rbuild handle containing information about the
        active stage.
        @param troveToDerive: troveTuple of binary which we wish to derive
    """

    targetLabel = handle.getProductStore().getActiveStageLabel()
    troveName = troveToDerive[0]
    # displaying output along the screen allows there to be a record
    # of what operations were performed.  Since this command is
    # an aggregate of several commands I think that is appropriate,
    # rather than simply using a progress callback.
    log.info('Shadowing %s=%s[%s] onto %s' % (troveToDerive[0],
                                             troveToDerive[1],
                                             troveToDerive[2],
                                             targetLabel))
    conaryFacade = handle.facade.conary

    conaryFacade.shadowSourceForBinary(troveToDerive[0],
                                       troveToDerive[1],
                                       troveToDerive[2],
                                       targetLabel)
    troveName = troveName.split(':')[0]
    conaryFacade.checkout(troveName, targetLabel)
    _writeDerivedRecipe(conaryFacade, troveName, directory=troveName)

    extractDir = '%s/%s/_ROOT_' % (os.getcwd(), troveName)
    log.info('extracting files from %s=%s[%s]' % troveToDerive)
    troveName, version, flavor = troveToDerive
    conaryFacade.checkoutBinaryPackage(troveName, version, flavor,
                                       extractDir)

def _writeDerivedRecipe(conaryFacade, troveName, directory):
    recipeName = troveName + '.recipe'
    recipePath = os.path.realpath(directory + '/' + recipeName)

    log.info('Removing extra files from checkout')
    conaryFacade._removeNonRecipeFilesFromCheckout(recipePath)
    log.info('Rewriting recipe file')
    recipeClass = conaryFacade._loadRecipeClassFromCheckout(recipePath)
    derivedRecipe = """
class %(className)s(DerivedPackageRecipe):
    name = '%(name)s'
    version = '%(version)s'

    def setup(r):
        pass

""" % dict(className=recipeClass.__name__,
           name=recipeClass.name,
           version=recipeClass.version)
    open(recipePath, 'w').write(derivedRecipe)
