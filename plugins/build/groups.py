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

def createRmakeJobForGroups(handle, groupList):
    return _createRmakeJobForGroups(handle, groupList)

def createRmakeJobForAllGroups(handle):
    return _createRmakeJobForGroups(handle)

def _createRmakeJobForGroups(handle, groupList=None):
    allRecipes = handle.productStore.getEditedRecipeDicts()
    _, groupRecipes = allRecipes
    if groupList is not None:
        groupRecipes = dict(x for x in groupRecipes.items() 
                          if x[0] in groupList)
        if len(groupRecipes) < len(groupList):
            notFound = set(groupList) - set(groupRecipes)
            raise errors.RbuildError(
                'the following groups'
                ' were not found: %s' % ', '.join(sorted(notFound)))
        assert(len(groupRecipes) == len(groupList))
    elif not groupRecipes:
        raise errors.RbuildError(
                'no groups are currently being edited - nothing to build')

    mainJob = _getJobBasedOnProductGroups(handle, groupRecipes)
    if mainJob is None:
        raise errors.RbuildError('No groups found to build')
    return mainJob

def _getJobBasedOnProductGroups(handle, groupRecipes, recurse=False):
    groupFlavors = handle.productStore.getGroupFlavors()
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

    label = handle.productStore.getActiveStageLabel()
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
                                                         recurse=recurse)
        return job
    else:
        return None
