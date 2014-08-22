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
Update packages and product definition source troves managed by Conary
"""

from rbuild import pluginapi
from rbuild.decorators import requiresStage
from rbuild.pluginapi import command


class PromoteCommand(pluginapi.command.BaseCommand):
    """Promote groups and packages to the next stage"""
    commands = ['promote']
    help = 'Promote groups and packages to next stage'
    docs = {
            'info' : 'Show what would be done but do not actually promote',
            }

    def addLocalParameters(self, argDef):
        argDef['info'] = command.NO_PARAM

    def runCommand(self, handle, argSet, args):
        """
        Process the command line provided for this plugin
        @param handle: context handle
        @type handle: rbuild.handle.RbuildHandle
        @param args: command-line arguments
        @type args: iterable
        """
        self.requireParameters(args)
        handle.Promote.promoteAll(infoOnly=argSet.get('info', False))


class Promote(pluginapi.Plugin):
    """
    Promote plugin
    """
    name = 'promote'

    def registerCommands(self):
        """
        Register the command-line handling portion of the promote plugin.
        """
        self.handle.Commands.registerCommand(PromoteCommand)

    @requiresStage
    def promoteAll(self, infoOnly=False):
        """
        Promote all appropriate troves from the currently active stage
        to the next stage.
        """
        store, product = self.handle.productStore, self.handle.product
        ui = self.handle.ui
        cny = self.handle.facade.conary

        activeStage = store.getActiveStageName()
        activeLabel = product.getLabelForStage(activeStage)
        nextStage = store.getNextStageName(activeStage)
        nextLabel = product.getLabelForStage(nextStage)

        # Collect a list of groups to promote.
        groupSpecs = [ '%s[%s]' % x for x in store.getGroupFlavors() ]
        ui.progress('Preparing to promote %d troves', len(groupSpecs))
        allTroves = cny._findTrovesFlattened(groupSpecs, activeLabel)

        # Get a list of all labels that are in the product's search
        # path (including subtroves).
        platformLabels = set()
        platformTroves = []
        for searchElement in product.getGroupSearchPaths():
            if searchElement.troveName:
                version = searchElement.label
                if searchElement.version:
                    version += '/' + searchElement.version
                platformTroves.append((searchElement.troveName, version, None))
            elif searchElement.label:
                platformLabels.add(searchElement.label)
        platformLabels.update(cny.getAllLabelsFromTroves(platformTroves))

        # Now get a list of all labels that are referenced by the
        # groups to be promoted but are not in the platform. These will
        # be "flattened" to the target label.
        flattenLabels = cny.getAllLabelsFromTroves(allTroves) - platformLabels
        fromTo = product.getPromoteMapsForStages(activeStage, nextStage,
                flattenLabels=flattenLabels)
        ui.info("The following promote map will be used:")
        for fromLabel, toBranch in sorted(fromTo.iteritems()):
            ui.info("  %s -- %s", fromLabel, toBranch)

        # Now promote.
        ui.progress('Promoting %d troves', len(groupSpecs))
        promotedList = cny.promoteGroups(allTroves, fromTo, infoOnly=infoOnly)
        promotedList = [ x for x in promotedList
                         if (':' not in x[0]
                             or x[0].split(':')[-1] == 'source') ]
        promotedList = [ '%s=%s[%s]' % (x[0], x[1].split('/')[-1], x[2])
                         for x in promotedList ]
        promotedList.sort()
        promotedTroveList = '\n   '.join(promotedList)
        if infoOnly:
            ui.write('The following would be promoted to %s:\n   %s',
                    nextStage, promotedTroveList)
        else:
            ui.write('Promoted to %s:\n   %s', nextStage, promotedTroveList)
        return promotedList, nextStage
