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


'''
unit tests for rmake facade
'''

import os

from rbuild_test import rbuildhelp
from testutils import mock

from conary import versions
from conary.deps import deps
from conary.lib import cfgtypes
from conary import conarycfg

from rmake.build import buildcfg

from rbuild.facade import conaryfacade
from rbuild.facade import rmakefacade

from rbuild import errors as rbuilderrors





def mockedMethod(self, real, saveList, fakeReturn, *args):
    '''
    generic mocked method
    @param self: the real object to which the mocked method belongs
    @param real: C{None} or function (normally the real method) to call
    @param saveList: C{None} or list in which to save arguments
    @param fakeReturn: value to return if real is C{None}
    @param args: real arguments to method
    '''
    if saveList is not None:
        saveList.append(args)
    if real:
        return real(self, *args)
    else:
        return fakeReturn

def mockedFunction(real, saveList, fakeReturn, *args):
    '''
    generic mocked function
    @param real: C{None} or function (normally the real function) to call
    @param saveList: C{None} or list in which to save arguments
    @param fakeReturn: value to return if real is C{None}
    @param args: real arguments to function
    '''
    if saveList is not None:
        saveList.append(args)
    if real:
        return real(*args)
    else:
        return fakeReturn

class MockConfig(object):
    def __init__(self, serverUrl=None):
        self.serverUrl = serverUrl
        self.includedConfigFile = None
        self.repositoryMap = {'a' : 'b'}
        self.user = ('foo', 'bar')
        self.name = None
        self.rmakeUrl = 'unix://var/lib/rmake/socket2'
        self.rmakeUser = None
        self.contact = None
        self.rmakePluginDirs = ['/foo']
        self.signatureKey = 'ASDF'
        self.signatureKeyMap = {'foo': 'FDSA'}
    def includeConfigFile(self, path):
        self.includedConfigFile = path

class Facade(object):
    pass

class MockHandle(object):
    def __init__(self, serverUrl=None):
        self.serverUrl = serverUrl
        self._cfg = None
        self.facade = Facade()
        self.facade.conary = conaryfacade.ConaryFacade(self)
        self.productStore = mock.MockObject()
        self.product = mock.MockObject()
        self.ui = mock.MockObject()

    def _setServerUrl(self, serverUrl):
        self.serverUrl = serverUrl
    def getConfig(self):
        if self._cfg is None: 
            self._cfg = MockConfig(serverUrl=self.serverUrl)
        return self._cfg

class MockBuild(object):
    def __init__(self, baseFlavor):
        self.baseFlavor = baseFlavor
        self.groupName = 'group-dist'

    def getBaseFlavor(self):
        return self.baseFlavor


class RmakeFacadeTest(rbuildhelp.RbuildHelper):
    def getMockedHandle(self, serverUrl=None):
        return MockHandle(serverUrl=serverUrl)
    def getFacade(self, handle):
        return rmakefacade.RmakeFacade(handle)

    def prep(self):
        handle = self.getMockedHandle()
        handle.productStore.getCurrentStageName._mock.setReturn('devel')
        handle.productStore.getRmakeConfigPath._mock.setReturn(
                                                    self.workDir + '/rmakerc')
        facade = self.getFacade(handle)
        return handle, facade

    def test_getBaseRmakeConfig(self):
        # avoid finding any real rmakerc on testing system
        # that breaks plugin config option parsing, so add back in rmakeUrl
        class mockRmakeBuildContext(buildcfg.RmakeBuildContext):
            rmakeUrl   = (cfgtypes.CfgString, None)
            strictMode = (cfgtypes.CfgBool, False)
            rmakeUser  = (buildcfg.CfgUser, None)
            signatureKey = (conarycfg.CfgFingerPrint, None)
            signatureKeyMap = (conarycfg.CfgFingerPrintMap, None)
        bc = buildcfg.BuildConfiguration
        class mockBuildConfiguration(buildcfg.BuildConfiguration):
            _cfg_bases = [mockRmakeBuildContext]
            def __init__(s2, readConfigFiles=False, root='',
                         conaryConfig=None, serverConfig=None,
                         ignoreErrors=False, log=None, 
                         strictMode=None):
                root = self.workDir
                bc.__init__(s2, readConfigFiles, root, conaryConfig,
                            serverConfig, ignoreErrors, log, strictMode)

        _, facade = self.prep()
        self.mock(buildcfg, 'BuildConfiguration', mockBuildConfiguration)
        self.mock(buildcfg, 'RmakeBuildContext', mockRmakeBuildContext)

        def testOne(rmakeUrl, rmakeUser):
            oldHome = os.environ['HOME']
            try:
                os.environ['HOME'] = ''
                rmkcfg = facade._getBaseRmakeConfig()
            finally:
                os.environ['HOME'] = oldHome

            self.assertEquals(rmkcfg.rmakeUrl, rmakeUrl)
            self.assertEquals(rmkcfg.rmakeUser, rmakeUser)

        rmakeUrl = None
        rmakeUser = None
        testOne(rmakeUrl, rmakeUser)

        rmakeUrl = 'https://rmake.server:9999'
        rmakeUser = ('user', 'password')
        open(self.workDir + '/.rmakerc', 'w').write(
            'rmakeUrl %s\nrmakeUser %s %s\n' %(
             rmakeUrl, rmakeUser[0], rmakeUser[1]))
        testOne(rmakeUrl, rmakeUser)

    def test_getRmakeConfig(self):
        handle, facade = self.prep()
        handle.productStore.getActiveStageName._mock.setReturn('devel')
        handle.product.getLabelForStage._mock.setReturn('localhost@rpl:1-devel',
                                                 'devel')
        handle.product.getBaseFlavor._mock.setReturn('foo,bar')
        upstreamSource = mock.MockObject(getTroveTup=lambda: (
            'foo', 'bar.rpath.org@rpl:1', None),
            notResolveTrove=False,
            notGroupSearchPath=False)
        handle.product.getResolveTroves._mock.setReturn([upstreamSource])
        handle.product.getBuildDefinitions._mock.setReturn(
                                                    [MockBuild('bar,bam'),
                                                     MockBuild('foo,bam')])
        handle.productStore.getGroupFlavors._mock.setReturn([
                                                 ('group-dist', 'bar,bam'),
                                                  ('group-dist', 'foo,bam')])
        handle.productStore.getBootstrapTroves._mock.setReturn(
                [('chroot-init', None, None)])
        handle.productStore.getRPMRequirements._mock.setReturn(
                [deps.parseDep('trove: rpm:lib')])
        rmakeCfg, contextDict = facade._getRmakeConfigWithContexts()
        assert(rmakeCfg.resolveTrovesOnly)
        assert(rmakeCfg.shortenGroupFlavors)
        assert(rmakeCfg.ignoreExternalRebuildDeps)
        assert(rmakeCfg.strictMode)
        buildLabel = versions.Label('localhost@rpl:1-devel')
        installLabelPath = [buildLabel, versions.Label('bar.rpath.org@rpl:1')]
        baseFlavor = deps.parseFlavor('foo,bar')

        # make sure all rmake values are set as expected.
        self.assertEquals(rmakeCfg.buildLabel, buildLabel)
        self.assertEquals(rmakeCfg.installLabelPath, installLabelPath)
        self.assertEquals(rmakeCfg.flavor, [baseFlavor])
        self.assertEquals(rmakeCfg.buildFlavor, baseFlavor)
        self.assertEquals(rmakeCfg.resolveTroves, 
                          [[('foo', 'bar.rpath.org@rpl:1', None)]])
        self.assertEquals(sorted(rmakeCfg._sections.keys()), ['bar', 'foo'])
        self.assertEquals(str(rmakeCfg._sections['foo'].buildFlavor), 'bam,foo')

        self.assertEquals(rmakeCfg.repositoryMap, {'a': 'b'})
        self.assertEquals(list(rmakeCfg.user), [('localhost', 'foo', 'bar')])
        self.assertEquals(rmakeCfg.rmakeUrl, 'unix://var/lib/rmake/socket2')
        self.assertEquals(rmakeCfg.rmakeUser, ('foo', 'bar'))
        self.assertEquals(sorted(contextDict.items()),
                [('bam,bar', 'bar'),
                 ('bam,foo', 'foo')])
        self.assertEquals(rmakeCfg.signatureKey, 'ASDF')
        self.assertEquals(rmakeCfg.signatureKeyMap, {'foo': 'FDSA'})
        self.assertEquals(rmakeCfg.bootstrapTroves,
                [('chroot-init', None, None)])
        self.assertEquals(rmakeCfg.rpmRequirements,
                [deps.parseDep('trove: rpm:lib')])

        open(self.workDir + '/rmakerc', 'w')
        rmakeCfg2, contextDict2 = facade._getRmakeConfigWithContexts()
        assert(rmakeCfg2 is rmakeCfg)
        assert(contextDict2 is contextDict)
        rmakeCfg3 = facade._getRmakeConfig()
        assert(rmakeCfg3 is not rmakeCfg)
        self.assertEquals(rmakeCfg.buildLabel, buildLabel)
        rmakeCfg4 = facade._getRmakeConfig()
        assert(rmakeCfg3 is rmakeCfg4)

        # Test rmakeUser fallback
        alternate = ('alternate', 'credentials')
        handle.getConfig().rmakeUser = alternate
        rmakeCfg5 = facade._getRmakeConfig(useCache=False)
        self.failUnlessEqual(rmakeCfg5.rmakeUser, alternate)

        # test contextless fetch
        facade._plugins = None
        rmakeCfg6 = facade._getRmakeConfig(includeContext=False)
        self.assertNotEquals(facade._plugins, None)
        self.assertEquals(rmakeCfg6.buildLabel, None)
        self.assertEquals(rmakeCfg6.rmakeUrl, 'unix://var/lib/rmake/socket2')

    def test_getRmakeConfigSearchPathWithLabel(self):
        handle, facade = self.prep()
        handle.productStore.getActiveStageName._mock.setReturn('devel')
        handle.product.getLabelForStage._mock.setReturn('localhost@rpl:1-devel',
                                                 'devel')
        handle.product.getBaseFlavor._mock.setReturn('foo,bar')
        upstreamSources = [
            mock.MockObject(getTroveTup=lambda x=x: x)
                for x in [ ('foo', 'bar.rpath.org@rpl:1', None),
                           (None, 'bar.rpath.org@rpl:2', None) ] ]
        handle.product.getResolveTroves._mock.setReturn(upstreamSources)
        handle.product.getBuildDefinitions._mock.setReturn(
                                                    [MockBuild('bar,bam'),
                                                     MockBuild('foo,bam')])
        handle.productStore.getGroupFlavors._mock.setReturn([
                                                 ('group-dist', 'bar,bam'),
                                                  ('group-dist', 'foo,bam')])


        rmakeCfg, contextDict = facade._getRmakeConfigWithContexts()
        self.failUnlessEqual([ str(x) for x in rmakeCfg.installLabelPath ],
            ['localhost@rpl:1-devel', upstreamSources[0].getTroveTup()[1],
             upstreamSources[1].getTroveTup()[1]])
        self.failUnlessEqual(rmakeCfg.resolveTroves,
            [[upstreamSources[0].getTroveTup()]])

    def testGetRmakeHelperWithContexts(self):
        _, facade = self.prep()
        mock.mockMethod(facade._getRmakeConfigWithContexts)
        mockConfig = mock.MockObject()
        mockConfig.getServerUri._mock.setReturn('http://fake.host:9999/')
        facade._getRmakeConfigWithContexts._mock.setReturn((mockConfig, {}))
        helper, contextDict = facade._getRmakeHelperWithContexts()
        self.assertEquals(contextDict, {})
        assert(helper.buildConfig is mockConfig)

    def testGetRmakeHelper(self):
        _, facade = self.prep()
        mock.mockMethod(facade._getRmakeConfig)
        mockConfig = mock.MockObject()
        mockConfig.getServerUri._mock.setReturn('http://fake.host:9999/')
        facade._getRmakeConfig._mock.setReturn(mockConfig)
        helper = facade._getRmakeHelper()
        assert(helper.buildConfig is mockConfig)

    def testCreateBuildJobForStage(self):
        handle, facade = self.prep()
        handle.productStore.getActiveStageName._mock.setDefaultReturn('QA')
        handle.productStore.getActiveStageLabel._mock.setReturn('localhost@foo:bar')
        handle.product.getGroupSearchPaths._mock.setReturn([])

        # rMake helper setup
        mock.mockMethod(facade._getRmakeConfigWithContexts)
        buildConfig = facade._getRmakeConfigWithContexts()[0]
        buildConfig._mock.set(resolveTroves=[])

        mock.mockMethod(facade._getRmakeHelperWithContexts)
        rmakeClient = facade._getRmakeHelperWithContexts()[0]
        rmakeClient._mock.enable('BUILD_RECURSE_GROUPS_SOURCE')
        rmakeClient.BUILD_RECURSE_GROUPS_SOURCE = 'z'

        # Set up the createBuildJob argument check and the job it returns
        buildJob = mock.MockObject()
        trv = mock.MockObject(cfg=buildConfig)
        buildJob.iterTroves._mock.setReturn([trv])
        rmakeClient.createBuildJob._mock.setDefaultReturn(buildJob)
        mock.mockMethod(handle.facade.conary._findTroves)
        handle.facade.conary._findTroves._mock.setDefaultReturn({})

        facade.createBuildJobForStage(['a', 'b', 'c'])
        handle.ui.progress._mock.assertCalled(
            'Creating rMake build job for 3 items')
        rmakeClient.createBuildJob._mock.assertCalled(['a', 'b', 'c'],
            rebuild=True, recurseGroups='z',
            limitToLabels=['localhost@foo:bar'], buildConfig=buildConfig)

    def testCreateBuildJobWithLocals(self):
        handle, facade = self.prep()
        mock.mockMethod(facade._getRmakeHelperWithContexts)
        rmakeClient = facade._getRmakeHelperWithContexts()[0]
        handle.productStore.getGroupFlavors._mock.setDefaultReturn([])
        handle.productStore.getActiveStageName._mock.setDefaultReturn('QA')
        handle.productStore.getActiveStageLabel._mock.setReturn('localhost@foo:bar')

        devTup = ('group-dev', 'example.devenv@rpl:2/5-6-7', None)
        devPathItem = mock.MockObject(
            getTroveTup=lambda: devTup,
            isResolveTrove=True,
            isGroupSearchPath=False
        )
        osTup = ('group-os', 'example.distro@rpl:2/1-2-3', None)
        osPathItem = mock.MockObject(
            getTroveTup=lambda: osTup,
            isResolveTrove=True,
            isGroupSearchPath=True
        )
        # This basically means "do not pin this" and will not be used
        # for package builds
        dynTup = ('dynamic', 'example.dyn@rpl:2/3-5-7', None)
        dynPathItem = mock.MockObject(
            getTroveTup=lambda: dynTup,
            isResolveTrove=False,
            isGroupSearchPath=True
        )
        # We don't know what this means yet, but whatever it
        # means, we shouldn't actually use it anywhere
        oddTup = ('weirdo', 'example.huh@rpl:2/2-4-6', None)
        oddPathItem = mock.MockObject(
            getTroveTup=lambda: oddTup,
            isResolveTrove=False,
            isGroupSearchPath=False
        )
        handle.product.getSearchPaths._mock.setReturn(
            [devPathItem, osPathItem, dynPathItem, oddPathItem])
        handle.product.getResolveTroves._mock.setReturn(
            [devPathItem, osPathItem])
        handle.product.getGroupSearchPaths._mock.setReturn(
            [osPathItem, dynPathItem])

        friendTup = ('friend', 'localhost@foo:bar/4-5-6', None)
        mock.mockMethod(handle.facade.conary.getLatestPackagesOnLabel)
        handle.facade.conary.getLatestPackagesOnLabel._mock.setReturn(
            [friendTup], 'localhost@foo:bar')

        def createBuildJob(itemList, rebuild=False, recurseGroups=False,
                           limitToLabels=None, buildConfig=None, **kwargs):
            self.assertEquals(itemList, ['a', 'b', 'c'])
            self.assertEquals((rebuild, recurseGroups), (False, False))
            self.assertEquals(limitToLabels, ['localhost@foo:bar'])
            self.assertEquals(buildConfig.resolveTroves[0], [friendTup])
            buildConfig.resolveTroveTups = buildConfig.resolveTroves

            job = mock.MockObject()
            trv = mock.MockObject(cfg=buildConfig)
            job.iterTroves._mock.setReturn([trv])
            return job
        rmakeClient._mock.set(createBuildJob=createBuildJob)

        mock.mockMethod(handle.facade.conary._findTroves)
        handle.facade.conary._findTroves._mock.setDefaultReturn(
            {dynTup: [dynTup]})

        job = facade.createBuildJobForStage(['a', 'b', 'c'], recurse=False,
            rebuild=False, useLocal=True)

        # Note: devTup[0:2] not in there!
        macros = job.iterTroves()[0].cfg.macros
        self.assertEquals(
            macros['productDefinitionSearchPath'],
            '%s=%s\n%s=%s' % (osTup[0:2] + dynTup[0:2]))

        # missing troves are an error
        handle.facade.conary._findTroves._mock.setDefaultReturn({})
        self.assertRaises(rbuilderrors.MissingGroupSearchPathElementError,
            facade.createBuildJobForStage, ['a', 'b', 'c'], recurse=False,
            rebuild=False, useLocal=True)

    def testBuildJob(self):
        _, facade = self.prep()
        mock.mockMethod(facade._getRmakeHelper)
        client = mock.MockObject()
        facade._getRmakeHelper._mock.setDefaultReturn(client)
        facade.buildJob(1)
        client.buildJob._mock.assertCalled(1)

    def testWatchAndCommitJob(self):
        _, facade = self.prep()
        mock.mockMethod(facade._getRmakeHelper)
        client = mock.MockObject()
        facade._getRmakeHelper._mock.setDefaultReturn(client)
        facade.watchAndCommitJob(1, '')
        client.watch._mock.assertCalled(1, commit=True, showTroveLogs=True,
            showBuildLogs=True, message='Automatic commit by rbuild')

    def testWatchJob(self):
        _, facade = self.prep()
        mock.mockMethod(facade._getRmakeHelper)
        client = mock.MockObject()
        facade._getRmakeHelper._mock.setDefaultReturn(client)
        facade.watchJob(1)
        client.watch._mock.assertCalled(1, showTroveLogs=True,
                                        showBuildLogs=True, exitOnFinish=1)

    def testIsJobBuilt(self):
        _, facade = self.prep()
        client = mock.MockObject()
        job = mock.MockObject()
        job.isBuilt._mock.setDefaultReturn(True)
        client.getJob._mock.setDefaultReturn(job)
        mock.mockMethod(facade._getRmakeHelper, client)

        rc = facade.isJobBuilt(1)
        client.getJob._mock.assertCalled(1)
        job.isBuilt._mock.assertCalled()
        assert(rc==True)

    def testGetBuildIdsFromJobId(self):
        _, facade = self.prep()
        client = mock.MockObject()
        job = mock.MockObject()
        build = mock.MockObject()
        troves = mock.MockObject()

        build.getImageBuildId._mock.setDefaultReturn(1)
        troves.values._mock.setDefaultReturn([build])
        job._mock.enable(troves)
        job._mock.set(troves=troves)
        client.getJob._mock.setDefaultReturn(job)
        mock.mockMethod(facade._getRmakeHelper, client)

        rc = facade.getBuildIdsFromJobId(42)
        client.getJob._mock.assertCalled(42)
        assert(rc==[1])

    def testOverlayJob(self):
        _, facade = self.prep()
        configDict1 = {'' : mock.MockObject(prebuiltBinaries=['a']),
                      'x86': mock.MockObject(buildTroveSpecs=['b', 'c']),
                      'x86_64' : mock.MockObject(buildTroveSpecs=['d', 'e']) }
        configDict2 = {'' : mock.MockObject(prebuiltBinaries=['f']),
                      'x86': mock.MockObject(buildTroveSpecs=['g', 'h']),
                      'x86_64' : mock.MockObject(buildTroveSpecs=['i', 'j']) }
        job1 = mock.MockObject()
        job2 = mock.MockObject()
        job1.getConfigDict._mock.setReturn(configDict1)
        job2.getConfigDict._mock.setReturn(configDict2)
        job1.getMainConfig._mock.setReturn(configDict1[''])
        job2.getMainConfig._mock.setReturn(configDict2[''])
        trv1 = mock.MockObject()
        job2.iterTroves()._mock.setList([trv1])
        job2.iterTroveList()._mock.setList([('a', 'b', 'c', 'd')])
        job1.getMainConfig()._mock.enable('primaryTroves')
        job1.getMainConfig()._mock.enable('prebuiltBinaries')
        assert(facade.overlayJob(job1, job2) == job1)
        job1.addBuildTrove._mock.assertCalled(trv1)
        assert(job1.getMainConfig().primaryTroves == [('a', 'b', 'c', 'd')])
        assert(job1.getConfigDict()['x86_64'].buildTroveSpecs == 
               ['d', 'e', 'i', 'j'])
        assert(job1.getMainConfig().prebuiltBinaries == ['a', 'f'])
        job1.iterTroveList()._mock.setList([('e', 'f', 'g', 'h')])
        assert(facade.overlayJob(None, job1) == job1)
        assert(job1.getMainConfig().primaryTroves == [('e', 'f', 'g', 'h')])

    def testGetRmakeContexts(self):
        _, facade = self.prep()
        mock.mockMethod(facade._getRmakeConfigWithContexts, ('foo', 'bar'))
        assert(facade._getRmakeContexts() == 'bar')

    def testDisplayJob(self):
        _, facade = self.prep()
        from rmake.cmdline import query
        mock.mock(query, 'displayJobInfo')
        mock.mockMethod(facade._getRmakeHelper)
        facade.displayJob(10, ['foo'], showLogs=True)
        query.displayJobInfo._mock.assertCalled(facade._getRmakeHelper(), 
                                                10, ['foo'], showLogs=True,
                                                displayTroves=True)

    def testCreateImagesJobForStage(self):
        handle, facade = self.prep()
        handle.productStore.getActiveStageName._mock.setReturn('devel')
        handle.productStore.getActiveStageLabel._mock.setReturn(
                                                    'localhost@rpl:devel')
        handle.product.getProductShortname._mock.setReturn('product')
        handle.product.getProductVersion._mock.setReturn('1')

        build = mock.MockObject(containerTemplateRef='imageType')
        build.getBuildImageGroup._mock.setReturn('group-foo')
        build.getBuildName._mock.setReturn('Ann Image')
        build.getBuildImage._mock.setReturn(mock.MockObject(containerFormat='imageType',
                                                            fields={'foo' : 'bar'}))

        containerTemplate = mock.MockObject(fields={'foo': 'baz'})
        handle.product.getContainerTemplate._mock.setReturn(
            containerTemplate,
            'imageType', None
        )

        flavor = deps.parseFlavor('foo')
        handle.productStore.getBuildsWithFullFlavors._mock.setReturn(
                                                            [(build, flavor)],
                                                            'devel')
        mock.mockMethod(facade._getRmakeHelper)
        facade.createImagesJobForStage()
        facade._getRmakeHelper().createImageJob._mock.assertCalled('product', 
            [(('group-foo', 'localhost@rpl:devel', flavor), 'imageType', 
             {'foo': 'bar'}, 'Ann Image')])


    def testFilteredCreateImagesJobForStage(self):
        handle, facade = self.prep()
        handle.productStore.getActiveStageName._mock.setReturn('devel')
        handle.productStore.getActiveStageLabel._mock.setReturn(
                                                    'localhost@rpl:devel')
        handle.product.getProductShortname._mock.setReturn('product')
        handle.product.getProductVersion._mock.setReturn('1')

        containerTemplate = mock.MockObject(fields={'foo': 'george'})
        handle.product.getContainerTemplate._mock.setReturn(
            containerTemplate,
            'imageType', None
        )

        build = mock.MockObject(containerTemplateRef='imageType')
        build.getBuildImageGroup._mock.setReturn('group-foo')
        build.getBuildName._mock.setReturn('Ann Image')
        build.getBuildImage._mock.setReturn(mock.MockObject(containerFormat='imageType',
                                                    fields={'foo' : 'bar'}))
        flavor = deps.parseFlavor('is: x86')
        build2 = mock.MockObject(containerTemplateRef='imageType')
        build2.getBuildImageGroup._mock.setReturn('group-foo2')
        build2.getBuildName._mock.setReturn('Ann Other Image')
        build2.getBuildImage._mock.setReturn(mock.MockObject(containerFormat='imageType',
                                                    fields={'foo' : 'baz'}))
        flavor2 = deps.parseFlavor('is: x86 x86_64')
        handle.productStore.getBuildsWithFullFlavors._mock.setReturn(
                                                            [(build, flavor),
                                                            (build2, flavor2)],
                                                            'devel')
        mock.mockMethod(facade._getRmakeHelper)
        facade.createImagesJobForStage()
        facade._getRmakeHelper().createImageJob._mock.assertCalled('product', [
             (('group-foo', 'localhost@rpl:devel', flavor), 'imageType', 
                 {'foo': 'bar'}, 'Ann Image'),
             (('group-foo2', 'localhost@rpl:devel', flavor2), 'imageType', 
                 {'foo': 'baz'}, 'Ann Other Image'),
            ])
        facade.createImagesJobForStage('Ann Image')
        facade._getRmakeHelper().createImageJob._mock.assertCalled('product', [
             (('group-foo', 'localhost@rpl:devel', flavor), 'imageType', 
                 {'foo': 'bar'}, 'Ann Image'),
            ])


