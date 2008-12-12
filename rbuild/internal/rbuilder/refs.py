#
# Copyright (c) 2005-2008 rPath, Inc.
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

import sys
from rbuild import pluginapi
from rbuild.pluginapi import command

from conary.deps import deps

class RbuilderReferencesCommand(command.BaseCommand):
    """
    lists references (shadows, etc.) to a trove
    """

    commands = ['find-refs']
    help = 'list references to a trove'
    docs = {'flat-list': 'Show results in a flat list suitable for scripting.'}
    requireConfig = False

    def addLocalParameters(self, argDef):
        argDef["flat-list"] = command.NO_PARAM

    def _output(self, nvf, flatList, data):
        for projectId, refs in data.iteritems():
            if refs and not flatList:
                #TODO: Get the project name and fqdn
                #p = client.getProject(int(projectId))
                #print "%s (%s):" % (p.getName(), p.getFQDN())
                print "Project %d" % projectId
            for ref in refs:
                if ref:
                    if len(ref) == 2:
                        ref = (nvf[0], ref[0], ref[1])

                    flavor = deps.ThawFlavor(ref[2])

                    flavorDifs = deps.flavorDifferences([nvf[2], flavor], strict = False)

                    if flatList:
                        print "%s=%s[%s]" % (ref[0], ref[1], flavor)
                    else:
                        diff = (not flavorDiffs[flavor].isEmpty()) and ("[%s]" % flavorDiffs[flavor]) or ""
                        print "\t%s=%s%s" % (ref[0], ref[1], diff)

    #pylint: disable-msg=R0201,R0903
    # could be a function, and too few public methods
    def runCommand(self, handle, argSet, args):
        args = args[2:]
        if len(args) < 1:
            return self.usage()

        flatList = argSet.pop('flat-list', False)

        # resolve a trovespec
        res = handle.facade.conary._findTroves([args[0]])

        n, v, f = res.values()[0][0]

        cfg = handle.facade.conary.getConaryConfig()
        queryFlavor = deps.flavorDifferences(cfg.flavor + [f], strict=False)[f]

        if not flatList:
            print "Projects that include a reference to %s=%s[%s]:\n" % (n, str(v), str(queryFlavor))
        r = handle.facade.rbuilder._getRbuilderClient().server.getTroveReferences(n, str(v), [f.freeze()])
        self._output((n,v,f), flatList, r)
        if not flatList:
            print "\nProjects that derive %s=%s[%s]:\n" % (n, str(v), str(queryFlavor))
        d = handle.facade.rbuilder._getRbuilderClient().server.getTroveDescendants(n, str(v.branch()), f.freeze())
        self._output((n,v,f), flatList, d)

