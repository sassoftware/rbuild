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
Update packages and product definition source troves managed by Conary
"""
from rbuild import pluginapi

class PromoteCommand(pluginapi.command.BaseCommand):
    """
    Updates source directories
    """
    commands = ['promote']
    help = 'Promote groups and packages to next stage'
    def runCommand(self, handle, _, args):
        """
        Process the command line provided for this plugin
        @param handle: context handle
        @type handle: rbuild.handle.RbuildHandle
        @param args: command-line arguments
        @type args: iterable
        """
        _ = self.requireParameters(args)
        promotedList, nextStage = handle.Promote.promoteAll()


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

    def promoteAll(self):
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

        # Now promote.
        fromTo = product.getPromoteMapsForStages(activeStage, nextStage,
                flattenLabels=flattenLabels)
        ui.progress('Promoting %d troves', len(groupSpecs))
        promotedList = cny.promoteGroups(allTroves, fromTo)
        promotedList = [ x for x in promotedList
                         if (':' not in x[0]
                             or x[0].split(':')[-1] == 'source') ]
        promotedList = [ '%s=%s[%s]' % (x[0], x[1].split('/')[-1], x[2])
                         for x in promotedList ]
        promotedList.sort()
        promotedTroveList = '\n   '.join(promotedList)
        ui.write('Promoted to %s:\n   %s', nextStage, promotedTroveList)
        return promotedList, nextStage
