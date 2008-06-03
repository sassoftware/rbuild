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
from rbuild import errors

from conary.lib import log

def createRmakeJobForPackages(handle, packageList):
    allRecipes = handle.getProductStore().getEditedRecipeDicts()
    packageRecipes, groupRecipes = allRecipes
    packageRecipes = dict(x for x in packageRecipes.items() 
                          if x[0] in packageList)
    if len(packageRecipes) < len(packageList):
        notFound = set(packageList) - set(packageRecipes)
        raise errors.RbuildError(
            'the following packages'
            ' were not found: %s' % ', '.join(sorted(notFound)))
    assert(len(packageRecipes) == len(packageList))
    mainJob = _getJobBasedOnProductGroups(handle, groupRecipes)
    # overlay the main job with the recipes that are checked out.
    return _addInEditedPackages(handle, mainJob, packageRecipes)

def createRmakeJobForAllPackages(handle):
    """
    Builds a job that could possibly build all packages that are defined
    by this product - but uses the edited packages list to set the primary
    list of packages to be built.  Only primary packages will be built
    automatically, others will be built if they require a primary package
    as a build dependency.
    @param handle: rbuild handle
    """
    allRecipes = handle.getProductStore().getEditedRecipeDicts()
    packageRecipes, groupRecipes = allRecipes

    if not packageRecipes:
        raise errors.RbuildError(
                'no packages are currently being edited - nothing to build')

    mainJob = _getJobBasedOnProductGroups(handle, groupRecipes)
    # overlay the main job with the recipes that are checked out.
    return _addInEditedPackages(handle, mainJob, packageRecipes)

def _getJobBasedOnProductGroups(handle, groupRecipes):
    groupFlavors = handle.getProductStore().getGroupFlavors()
    if not (groupFlavors or groupRecipes):
        return None
    contextDict = handle.facade.rmake._getRmakeContexts()

    groupsToFind = {}
    recipesToBuild = []
    for groupName, flavor in groupFlavors:
        context = contextDict[flavor]
        if groupName in groupRecipes:
            # build recipe instead of whatever is in the repository
            recipesToBuild.append(groupRecipes[groupName] + '{%s}' % context)
        else:
            groupsToFind.setdefault(
                    (groupName + ':source', None, None), []).append(context)

    label = handle.getProductStore().getActiveStageLabel()
    results = handle.facade.conary._findTroves(groupsToFind.keys(), label,
                                               allowMissing=True)
    groupsToBuild = []
    for groupSpec in results.keys():
        for context in groupsToFind[groupSpec]:
            groupName = groupSpec[0].split(':')[0]
            groupsToBuild.append('%s{%s}' % (groupName, context))
    groupsToBuild += recipesToBuild

    if groupsToBuild:
        job = handle.facade.rmake.createBuildJobForStage(groupsToBuild,
                                                         recurse=True)
        return job
    else:
        return None

def _addInEditedPackages(handle, mainJob, packageRecipes):
    # remove packages from the main job that were going to be built from
    # the repository but now are being built from recipes.
    replacementRecipes, newRecipeDict = _removePackagesWithEditedReplacements(
                                            mainJob, packageRecipes)
    if newRecipeDict:
        # if we don't find a match in a group, that means no one has
        # told us what flavor to build this package with.  We'll build it
        # once per context we know about.
        log.warning('the following edited packages were not in any groups'
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
