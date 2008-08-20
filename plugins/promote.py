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
        promotedList = '\n   '.join(promotedList)
        print 'Promoted to %s:\n   %s' % (nextStage, promotedList)


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
        cny = self.handle.facade.conary

        activeStage = store.getActiveStageName()
        nextStage = store.getNextStageName(activeStage)
        activeLabel = self.handle.product.getLabelForStage(activeStage)

        fromTo = self.handle.product.getPromoteMapsForStages(activeStage, nextStage)

        groupSpecs = [ '%s[%s]' % x for x in store.getGroupFlavors() ]
        allTroves = cny._findTrovesFlattened(groupSpecs, activeLabel)
        promotedList = cny.promoteGroups(allTroves, fromTo)

        promotedList = [ x for x in promotedList
                         if (':' not in x[0]
                             or x[0].split(':')[-1] == 'source') ]
        promotedList = [ '%s=%s[%s]' % (x[0], x[1].split('/')[-1], x[2])
                         for x in promotedList ]
        promotedList.sort()
        return promotedList, nextStage
