#
# Copyright (c) SAS Institute Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
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
