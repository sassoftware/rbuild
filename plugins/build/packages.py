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


from rbuild import errors
from rbuild_plugins.build import groups

def createRmakeJobForPackages(handle, packageList, recurse=True):
    return _createRmakeJobForPackages(handle, packageList, recurse)

def createRmakeJobForAllPackages(handle):
    """
    Builds a job that could possibly build all packages that are defined
    by this product - but uses the edited packages list to set the primary
    list of packages to be built.  Only primary packages will be built
    automatically, others will be built if they require a primary package
    as a build dependency.
    @param handle: rbuild handle
    """
    return _createRmakeJobForPackages(handle)

def _createRmakeJobForPackages(handle, packageList=None, recurse=True):
    if packageList and not recurse:
        return _getJobFromNames(handle, packageList)
    else:
        allRecipes = handle.productStore.getEditedRecipeDicts()
        packageRecipes, groupRecipes = allRecipes
        if packageList is not None:
            packageRecipes = dict(x for x in packageRecipes.items() 
                                  if x[0] in packageList)
            if len(packageRecipes) < len(packageList):
                notFound = set(packageList) - set(packageRecipes)
                raise errors.PluginError(
                    'the following packages'
                    ' were not found: %s' % ', '.join(sorted(notFound)))
            assert(len(packageRecipes) == len(packageList))
        elif not packageRecipes:
            raise errors.PluginError(
                    'no packages are currently being edited - nothing to build')

        mainJob = groups._getJobBasedOnProductGroups(handle, groupRecipes,
                                                     recurse=True)
        # overlay the main job with the recipes that are checked out.
        return _addInEditedPackages(handle, mainJob, packageRecipes)


def _getJobFromNames(handle, packageList):
    """
    Build everything in C{packageList} without a rebuild and without
    recursing into the image group.
    """
    packageRecipes, groupRecipes = handle.productStore.getEditedRecipeDicts()

    flavors = set(x[1] for x in handle.productStore.getGroupFlavors())
    contexts = handle.facade.rmake._getRmakeContexts()

    if not flavors:
        raise errors.PluginError("no image flavors defined; "
            "don't know what to build")

    toBuild = []
    for name in packageList:
        if name in packageRecipes:
            name = packageRecipes[name]
        elif name in groupRecipes:
            name = groupRecipes[name]

        for flavor in flavors:
            context = contexts[flavor]
            toBuild.append('%s{%s}' % (name, context))

    return handle.facade.rmake.createBuildJobForStage(toBuild,
        recurse=False, rebuild=False, useLocal=True)


def _addInEditedPackages(handle, mainJob, packageRecipes):
    # remove packages from the main job that were going to be built from
    # the repository but now are being built from recipes.
    replacementRecipes, newRecipeDict = _removePackagesWithEditedReplacements(
                                            mainJob, packageRecipes)
    if newRecipeDict:
        # if we don't find a match in a group, that means no one has
        # told us what flavor to build this package with.  We'll build it
        # once per context we know about.
        handle.ui.warning(
                    'the following edited packages were not in any groups'
                    ' or have not been committed yet - building with default'
                    ' flavors: %s' % ', '.join(sorted(newRecipeDict.keys())))
        contextDict = handle.facade.rmake._getRmakeContexts()
        for recipePath in newRecipeDict.values():
            for context in contextDict.values():
                replacementRecipes.append('%s{%s}' % (recipePath, context))
    recipeJob = handle.facade.rmake.createBuildJobForStage(replacementRecipes)
    return handle.facade.rmake.overlayJob(mainJob, recipeJob)

def _removePackagesWithEditedReplacements(mainJob, packageRecipes):
    newRecipes = packageRecipes.copy()
    if mainJob is None:
        return [], newRecipes
    replacementRecipes = []
    for troveTup in list(mainJob.iterTroveList(withContexts=True)):
        packageName = troveTup[0].split(':')[0]
        if packageName in packageRecipes:
            mainJob.removeTrove(*troveTup)
            recipeItem = '%s[%s]{%s}' % (packageRecipes[packageName],
                                         troveTup[2],
                                         troveTup[3])
            replacementRecipes.append(recipeItem)
            newRecipes.pop(packageName, False)
        elif troveTup[0].startswith('group-'):
            mainJob.removeTrove(*troveTup)
            newRecipes.pop(packageName, False)
    return replacementRecipes, newRecipes
