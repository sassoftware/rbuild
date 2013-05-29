#!/usr/bin/python
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



from testutils import mock

from rbuild_test import rbuildhelp

class PromoteTest(rbuildhelp.RbuildHelper):
    def testCommand(self):
        self.getRbuildHandle()
        self.checkRbuild('promote',
                'rbuild_plugins.promote.Promote.promoteAll', [None],
                infoOnly=False)

    def testPromoteAll(self):
        productStore = mock.MockObject()
        handle = self.getRbuildHandle(productStore=productStore)
        mock.mock(handle.facade, 'conary')
        facade = handle.facade.conary
        handle.product = mock.MockObject()
        productStore._mock.set(_handle=handle)

        # Fake stages
        productStore.getActiveStageName._mock.setReturn('Development')
        productStore.getNextStageName._mock.setReturn('Quality', 'Development')
        handle.product.getLabelForStage._mock.setReturn('localhost@rpl:devel',
                                                      'Development')
        handle.product.getLabelForStage._mock.setReturn('localhost@rpl:qa',
                                                      'Quality')

        # Fake product frumptuu
        map = { 'localhost@rpl:devel': '/localhost@rpl:qa', # basic
                'localhost@rpl:java-devel': '/localhost@rpl:java-qa', # secondary
                'localhost@extra:devel': 'localhost@extra:qa', # promoteMap
                'contrib@rpl:2': '/localhost@rpl:qa', # flatten
              }
        handle.product.getPromoteMapsForStages._mock.setReturn(map,
                'Development', 'Quality', flattenLabels=set([
                    'localhost@rpl:java-devel', 'contrib@rpl:2',
                    'localhost@rpl:devel', 'localhost@extra:devel']))

        # Fake search path
        paths = [mock.MockObject() for x in range(3)]
        paths[0]._mock.set(troveName='group-rap-packages', label='rap.rpath.com@rpath:linux-2', version=None)
        paths[1]._mock.set(troveName='group-os', label='conary.rpath.com@rpl:2', version='2.0-1-1')
        paths[2]._mock.set(troveName=None, label='safe@rpl:2', version=None)
        handle.product.getGroupSearchPaths._mock.setReturn(paths)

        facade.getAllLabelsFromTroves._mock.setReturn(
                set(['rap.rpath.com@rpath:linux-2', 'conary.rpath.com@rpl:2']),
                [('group-rap-packages', 'rap.rpath.com@rpath:linux-2', None),
                    ('group-os', 'conary.rpath.com@rpl:2/2.0-1-1', None)])

        # Fake groups and promote
        productStore.getGroupFlavors._mock.setReturn(
            [('group-dist', 'is: x86'), ('group-dist', 'is: x86_64')])
        groupDist = [('group-dist', 
                      '/localhost@rpl:devel/1.0-1-1', 'is: x86_64'),
                      ('group-dist', '/localhost@rpl:devel/1.0-1-1', 'is: x86')]
        facade.getAllLabelsFromTroves._mock.setReturn(
                set(map.keys() + ['rap.rpath.com@rpath:linux-2']), groupDist)

        promoted = [
            ('group-dist', '/localhost@rpl:qa/1.0-1-1', 'is: x86_64'),
            ('group-dist', '/localhost@rpl:qa/1.0-1-1', 'is: x86'),
            ('group-dist:source', '/localhost@rpl:qa/1.0-1', ''),
            ('setup:source', '/localhost@rpl:qa/1.0-1', ''),
            ('setup:runtime', '/localhost@rpl:qa/1.0-1-1', ''),
            ('setup', '/localhost@rpl:qa/1.0-1-1', ''),
            ('kernel:source', '/localhost@xen:qa/1.0-1', ''),
            ('kernel:runtime', '/localhost@xen:qa/1.0-1-1', ''),
            ('kernel', '/localhost@xen:qa/1.0-1-1', ''),
            ('java:source', '/otherhost@rpl:java-qa/1.0-1', ''),
            ('java', '/otherhost@rpl:java-qa/1.0-1-1', ''),
          ]
        facade._findTrovesFlattened._mock.setReturn(groupDist,
                 ['group-dist[is: x86]', 'group-dist[is: x86_64]'],
                 'localhost@rpl:devel')
        facade.promoteGroups._mock.setReturn(promoted, groupDist, map,
                infoOnly=False)
        facade.promoteGroups._mock.setReturn(promoted, groupDist, map,
                infoOnly=True)

        # First an info-only pass
        promotedList, stage = self.captureOutput(handle.Promote.promoteAll,
                infoOnly=True)[0]
        self.assertEqual(stage, 'Quality')
        expected = [
            'group-dist:source=1.0-1[]', 
            'group-dist=1.0-1-1[is: x86]', 
            'group-dist=1.0-1-1[is: x86_64]', 
            'java:source=1.0-1[]',
            'java=1.0-1-1[]',
            'kernel:source=1.0-1[]',
            'kernel=1.0-1-1[]',
            'setup:source=1.0-1[]',
            'setup=1.0-1-1[]',
          ]
        self.assertEqual(promotedList, expected)

        # Check the outcome of the promote
        promotedList, stage = self.captureOutput(handle.Promote.promoteAll)[0]
        self.assertEqual(stage, 'Quality')
        self.assertEqual(promotedList, expected)
