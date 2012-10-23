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
