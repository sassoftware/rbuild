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
