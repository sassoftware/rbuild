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
Contains the functions which derive a package.
"""

def derive(handle, troveToDerive):
    """
    Performs all the commands necessary to create a derived recipe.

    @param handle: rbuild handle containing information about the
    active stage.
    @param troveToDerive: troveTuple of binary which we wish to derive
    @return: directory in which checkout was created
    """

    ui = handle.ui
    targetLabel = handle.productStore.getActiveStageLabel()
    targetDir = handle.productStore.getCheckoutDirectory(troveToDerive[0])
    # displaying output along the screen allows there to be a record
    # of what operations were performed.  Since this command is
    # an aggregate of several commands I think that is appropriate,
    # rather than simply using a progress callback.
    ui.info('Shadowing %s=%s[%s] onto %s', troveToDerive[0],
                                           troveToDerive[1],
                                           troveToDerive[2],
                                           targetLabel)
    conaryFacade = handle.facade.conary
    conaryFacade.derive(troveToDerive,targetLabel,targetDir)
    return targetDir
