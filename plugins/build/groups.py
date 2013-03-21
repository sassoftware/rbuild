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
            raise errors.PluginError(
                'the following groups'
                ' were not found: %s' % ', '.join(sorted(notFound)))
        assert(len(groupRecipes) == len(groupList))
    elif not groupRecipes:
        raise errors.PluginError(
                'no groups are currently being edited - nothing to build')

    mainJob = _getJobBasedOnProductGroups(handle, groupRecipes)
    if mainJob is None:
        raise errors.PluginError('No groups found to build')
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
