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
unit tests for conary facade
'''


from rbuild_test import rbuildhelp
from testutils import mock
import os

from rbuild.facade import conaryfacade
from rbuild import errors

from conary import clone
from conary import conarycfg
from conary import conaryclient
from conary import checkin
from conary import errors as conaryerrors
from conary import updatecmd
from conary import state
from conary import versions
from conary.versions import VersionFromString as VFS
from conary.versions import Label
from conary.build import loadrecipe, use, errors as builderrors
from conary.deps import deps
from conary.deps.deps import parseFlavor as Flavor
from conary.lib import log


def mockedMethod(self, real, saveList, fakeReturn, *args, **kwargs):
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
        return real(self, *args, **kwargs)
    else:
        return fakeReturn

def mockedFunction(real, saveList, fakeReturn, *args, **kwargs):
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
        return real(*args, **kwargs)
    else:
        return fakeReturn

class MockConfig(object):
    def __init__(self, serverUrl=None):
        self.serverUrl = serverUrl
        self.includedConfigFile = None
        self.repositoryMap = {}
        self.user = []
        self.name = None
        self.contact = None
        self.signatureKey = None
        self.signatureKeyMap = {}
    def includeConfigFile(self, path):
        self.includedConfigFile = path
    
class MockHandle(object):
    def __init__(self, serverUrl=None):
        self.serverUrl = serverUrl
        self._cfg = None
        self.ui = mock.MockObject()

    def _setServerUrl(self, serverUrl):
        self.serverUrl = serverUrl
    def getConfig(self):
        if self._cfg is None: 
            self._cfg = MockConfig(serverUrl=self.serverUrl)
        return self._cfg

class MockRepositoryClient(object):
    def __init__(self):
        self.recordFindTroveArgs = []
        self.recordCommitChangeSetArgs = []

    # this method is sometimes overridden in subtests
    #pylint: disable-msg=E0202
    def findTroves(self, labelPath, troveSpecs, defaultFlavor=None, allowMissing=False):
        results = {}
        if labelPath:
            if not isinstance(labelPath, (tuple, list)):
                labelPath = labelPath,
            else:
                labelPath = tuple(labelPath)
        for troveSpec in troveSpecs:
            self.recordFindTroveArgs.append((labelPath, troveSpec))
            if troveSpec[2] is not None:
                flavor = troveSpec[2]
            else:
                flavor = deps.parseFlavor('')
            if labelPath:
                if troveSpec[1]:
                    verPart = troveSpec[1]
                else:
                    verPart = '1.0-1-1'
                troveTup = (troveSpec[0],
                            versions.VersionFromString('/%s/%s'%(
                                labelPath[0], verPart)),
                            flavor)
            else:
                troveTup = (troveSpec[0],
                            versions.VersionFromString(troveSpec[1]),
                            flavor)
            results[troveSpec] = [troveTup]
        return results

    def commitChangeSet(self, cs):
        self.recordFindTroveArgs.append(cs)



class ConaryFacadeTest(rbuildhelp.RbuildHelper):
    def getMockedHandle(self, serverUrl=None):
        return MockHandle(serverUrl=serverUrl)
    def getFacade(self, handle):
        return conaryfacade.ConaryFacade(handle)
    def prep(self):
        handle = self.getMockedHandle()
        facade = self.getFacade(handle)
        return handle, facade

    def prepReposState(self, facade):
        mock.mockMethod(facade._getRepositoryStateFromDirectory)
        repos = mock.MockObject()
        sourceState = mock.MockObject()
        facade._getRepositoryStateFromDirectory._mock.setDefaultReturn(
            [repos, sourceState])
        return (repos, sourceState)

    def testParseRBuilderConfigFile(self):
        handle, facade = self.prep()
        cfg = MockConfig()
        facade._parseRBuilderConfigFile(cfg)
        assert cfg.includedConfigFile is None

        handle._setServerUrl('http://conary.example.com')
        handle._cfg = None # cached config is now wrong, must regenerate
        facade._parseRBuilderConfigFile(cfg)
        assert cfg.includedConfigFile == 'http://conary.example.com/conaryrc'

    def xtestParseRBuilderConfigFile(self):
        handle, facade = self.prep()
        cfg = MockConfig()
        facade._parseRBuilderConfigFile(cfg)
        assert cfg.includedConfigFile is None

        handle._setServerUrl('http://conary.example.com')
        handle._cfg = None # cached config is now wrong, must regenerate
        facade._parseRBuilderConfigFile(cfg)
        assert cfg.includedConfigFile == 'http://conary.example.com/conaryrc'


    def testGetConaryClient(self):
        _, facade = self.prep()
        mock.mock(facade, 'getConaryConfig')
        facade.getConaryConfig._mock.setDefaultReturn('c')
        savedArgs = []
        self.mock(conaryclient, 'ConaryClient',
            lambda *args: mockedFunction(None, savedArgs, None, *args))
        facade._getConaryClient()
        assert savedArgs == [('c',)], \
                                'Failed to find return from getConaryConfig'

    def testGetRepositoryClient(self):
        _, facade = self.prep()
        mock.mock(facade, '_getConaryClient')
        conaryClient = mock.MockObject()
        conaryClient.getRepos._mock.setDefaultReturn('r')
        facade._getConaryClient._mock.setDefaultReturn(conaryClient)
        assert facade._getRepositoryClient() == 'r', \
                                'Failed to find return from getRepos'

    def testGetVersion(self):
        _, facade = self.prep()
        versionString = '/a@b:c/1.2-3-4'
        versionObject = versions.VersionFromString(versionString)
        assert facade._getVersion(versionString) == versionObject
        assert facade._getVersion(versionObject) == versionObject

    def testGetLabel(self):
        _, facade = self.prep()
        labelString = 'a@b:c'
        labelObject = versions.Label(labelString)
        assert facade._getLabel(labelString) == labelObject
        assert facade._getLabel(labelObject) == labelObject

        v1 = '/a@b:c'
        v2 = '/b@c:d/%s' % v1
        v3 = '%s/1.2.3-1-1' % v1
        assert facade._getLabel(v1) == labelObject
        assert facade._getLabel(v2) == labelObject
        assert facade._getLabel(v3) == labelObject

    def testGetFlavor(self):
        _, facade = self.prep()
        flavorString = '!bootstrap is:x86'
        flavorObject = deps.parseFlavor(flavorString)
        assert facade._getFlavor(flavorString) == flavorObject
        assert facade._getFlavor(flavorObject) == flavorObject
        flavorObject = deps.parseFlavor('') # same as deps.Flavor()
        assert facade._getFlavor() == flavorObject
        assert facade._getFlavor(None, keepNone=True) == None

    def testFindTrove(self):
        _, facade = self.prep()
        r = MockRepositoryClient()
        self.mock(conaryfacade.ConaryFacade, '_getRepositoryClient',
            lambda *args: mockedMethod(args[0], None, None, r, *args[1:]))
        # pointless to mock _getVersion and _getFlavor
        versionString = '/a@b:c/1.2.3-1'
        returnedTroveTup = facade._findTrove('foo:source', versionString)
        assert len(r.recordFindTroveArgs) == 1
        labelPath, troveTup = r.recordFindTroveArgs[0]
        name, versionObject, flavorObject = returnedTroveTup
        assert troveTup[1] == str(returnedTroveTup[1])
        assert labelPath is None
        assert name == 'foo:source'
        assert versionObject == versions.VersionFromString(versionString)
        assert flavorObject == deps.Flavor()

        r.recordFindTroveArgs = []
        returnedTroveTup = facade._findTrove('foo', '1.2.3-1-1',
                                             labelPath='a@b:c',
                                             flavor='bootstrap')
        assert len(r.recordFindTroveArgs) == 1
        labelPath, troveTup = r.recordFindTroveArgs[0]
        name, versionObject, flavorObject = returnedTroveTup
        # transformed due to labelPath:
        assert troveTup[1] != str(returnedTroveTup[1])
        assert labelPath == ('a@b:c',)
        assert name == 'foo'
        assert versionObject == versions.VersionFromString('/a@b:c/1.2.3-1-1')
        assert flavorObject == deps.parseFlavor('bootstrap')

        r.findTroves = lambda *args, **kw: {}
        returnedTroveTup = facade._findTrove('foo', '1.2.3-1-1',
                                             labelPath='a@b:c',
                                             flavor='bootstrap')
        assert(returnedTroveTup is None)

        def findTroves(*args, **kw):
            raise conaryerrors.LabelPathNeeded

        r.findTroves = findTroves
        self.assertRaises(errors.RbuildError, facade._findTrove, 
            'foo', '1.2.3-1-1')


    def testFindTroves(self):
        _, facade = self.prep()
        repos = MockRepositoryClient()
        mock.mockMethod(facade._getRepositoryClient, repos)
        results = facade._findTroves([('foo', None, None)],
                                    ['localhost@rpl:1', 'localhost@rpl:2'])
        assert(results == {('foo', None, None): 
                        [('foo', VFS('/localhost@rpl:1/1.0-1-1'), Flavor(''))]})
        results = facade._findTrovesFlattened([('foo', None, None)],
                                    ['localhost@rpl:1', 'localhost@rpl:2'])
        assert(results == [('foo', 
                            VFS('/localhost@rpl:1/1.0-1-1'), Flavor(''))])
        results = facade._findTroves(['foo[ssl]'], 'localhost@rpl:1')
        assert(results == {('foo[ssl]'): 
                    [('foo', VFS('/localhost@rpl:1/1.0-1-1'), Flavor('ssl'))]})
        results = facade._findTrovesFlattened(['foo[ssl]'], 'localhost@rpl:1')
        assert(results == [('foo',
                             VFS('/localhost@rpl:1/1.0-1-1'), Flavor('ssl'))])

    def testVersionToString(self):
        _, facade = self.prep()
        versionString = '/a@b:c/1.2-3-4'
        versionObject = versions.VersionFromString(versionString)
        assert facade._versionToString(versionString) == versionString
        assert facade._versionToString(versionObject) == versionString

    def testFlavorToString(self):
        _, facade = self.prep()
        flavorString = '!bootstrap is:x86'
        flavorObject = deps.parseFlavor(flavorString)
        flavorString = str(flavorObject) # get canonical representation
        assert facade._flavorToString(flavorObject) == flavorString
        assert facade._flavorToString(flavorString) == flavorString
        assert facade._flavorToString(None) == ''

    def testTroveTupToStrings(self):
        _, facade = self.prep()
        name = 'foo'
        versionString = '/a@b:c/1.2-3-4'
        flavorString = '!bootstrap is:x86'
        flavorObject = deps.parseFlavor(flavorString)
        flavorString = str(flavorObject) # get canonical representation
        returnTroveTup = facade._troveTupToStrings(name, versionString,
                                                   flavorString)
        returnName, returnVersionString, returnFlavorString = returnTroveTup
        assert returnName == name
        assert returnVersionString == versionString
        assert returnFlavorString == flavorString

    def testGetConaryConfig(self):
        handle, facade = self.prep()
        mockConaryConfig = MockConfig()
        handle.getConfig() # create handle._cfg
        handle._cfg.repositoryMap = {'foo': 'bar'}
        handle._cfg.user = ('rbuildCfgUser', 'rbuildCfgPassword')
        handle._cfg.name = 'rbuildCfgName'
        handle._cfg.contact = 'rbuildCfgContact'
        handle._cfg.signatureKey = 'ASDF'
        handle._cfg.signatureKeyMap = {'foo': 'FDSA'}
        self.mock(conarycfg, 'ConaryConfiguration',
            lambda *args: mockedFunction(None, None, mockConaryConfig, *args))
        facadeCfg = facade.getConaryConfig()
        self.assertEquals(facadeCfg.repositoryMap, handle._cfg.repositoryMap)
        self.assertEquals(facadeCfg.user, [('*', 'rbuildCfgUser', 'rbuildCfgPassword')])
        self.assertEquals(facadeCfg.name, handle._cfg.name)
        self.assertEquals(facadeCfg.contact, handle._cfg.contact)
        self.assertEquals(facadeCfg.signatureKey, 'ASDF')
        self.assertEquals(facadeCfg.signatureKeyMap, {'foo': 'FDSA'})
        facadeCfgCached = facade.getConaryConfig()
        self.assertEquals(facadeCfg, facadeCfgCached)

    def test_getBaseConaryConfig(self):
        _, facade = self.prep()
        def readFiles(s):
            s.read(self.workDir + '/conaryrc')
        self.mock(conarycfg.ConaryConfiguration, 'readFiles', readFiles)
        name = 'John Doe'
        contact = 'http://john.doe/'
        open(self.workDir + '/conaryrc', 'w').write(
            'name %s\ncontact %s\n' %(name, contact))
        ccfg = facade._getBaseConaryConfig()
        self.assertEquals(ccfg.name, name)
        self.assertEquals(ccfg.contact, contact)

    def testSetFactoryFlag(self):
        _, facade = self.prep()
        self.mock(checkin, 'factory', mock.MockObject())
        facade.setFactoryFlag(None)
        checkin.factory._mock.assertCalled('', targetDir=None)

        facade.setFactoryFlag(None, 'a')
        checkin.factory._mock.assertCalled('', targetDir='a')

    def testCheckout(self):
        _, facade = self.prep()
        mockConaryCfg = mock.MockObject()
        mock.mockMethod(facade.getConaryConfig)
        facade.getConaryConfig._mock.setDefaultReturn(mockConaryCfg)
        mock.mockMethod(facade._getRepositoryClient)
        facade._getRepositoryClient._mock.setDefaultReturn('r')
        savedArgs = []
        self.mock(checkin, 'checkout',
            lambda *args: mockedFunction(None, savedArgs, None, *args))
        facade.checkout('packageName', 'labelName', targetDir='targetDirName')
        expectedArgs = [('r', mockConaryCfg, 'targetDirName', 
                        ['packageName=labelName'])]
        assert savedArgs == expectedArgs

    def testDetachPackage(self):
        _, facade = self.prep()
        mockConaryCfg = mock.MockObject()
        mock.mockMethod(facade.getConaryConfig)
        facade.getConaryConfig._mock.setDefaultReturn(mockConaryCfg)
        mock.mock(clone, 'CloneTrove')
        troveSpec = self.makeTroveTuple('foo:source')
        facade.detachPackage(troveSpec, '/targetlabel.rpath.org@rpath:1')
        clone.CloneTrove._mock.assertCalled(mockConaryCfg,
            '/targetlabel.rpath.org@rpath:1', 
            [troveSpec[0]+'='+troveSpec[1].asString()],
            message='Automatic promote by rBuild.')
        facade.detachPackage(troveSpec, '/targetlabel.rpath.org@rpath:1', 'blech')
        clone.CloneTrove._mock.assertCalled(mockConaryCfg,
            '/targetlabel.rpath.org@rpath:1', 
            [troveSpec[0]+'='+troveSpec[1].asString()],
            message='blech')
    
    def testRefresh(self):
        handle, facade = self.prep()
        mockConaryCfg = mock.MockObject()
        mock.mockMethod(facade.getConaryConfig)
        facade.getConaryConfig._mock.setDefaultReturn(mockConaryCfg)
        mock.mockMethod(facade._getRepositoryClient)
        facade._getRepositoryClient._mock.setDefaultReturn('r')
        mock.mockMethod(facade._initializeFlavors)
        mock.mockFunction(use.setBuildFlagsFromFlavor)
        savedArgs = []
        self.mock(checkin, 'refresh',
            lambda *args, **kw: mockedFunction(None, savedArgs, None, *args))
        facade.refresh()
        expectedArgs = [('r', mockConaryCfg)]
        
        assert savedArgs == expectedArgs
        facade._initializeFlavors._mock.assertCalled()
        use.setBuildFlagsFromFlavor._mock.assertCalled(None,
            mockConaryCfg.buildFlavor, False)

    def testUpdateCheckout(self):
        _, facade = self.prep()
        mock.mockMethod(facade._getRepositoryClient)
        facade._getRepositoryClient._mock.setDefaultReturn('r')
        savedArgs = []
        self.mock(checkin, 'nologUpdateSrc',
            lambda *args: mockedFunction(None, savedArgs, True, *args))
        facade.updateCheckout('targetDirName')
        self.assertEquals(savedArgs, [('r', [
            os.sep.join((os.getcwd(), 'targetDirName'))])])

        # Up to date condition
        def Up2Date(*args):
            raise builderrors.UpToDate('testDirName')
        self.mock(checkin, 'nologUpdateSrc', Up2Date)
        self.assertEquals(True, facade.updateCheckout('targetDirName'))

        # note yet checked in
        def Up2Date(*args):
            raise builderrors.NotCheckedInError('testDirName')
        self.mock(checkin, 'nologUpdateSrc', Up2Date)
        self.assertEquals(True, facade.updateCheckout('targetDirName'))

        #Failure conditions
        savedArgs = []
        def attrErrorRaise(*args):
            raise AttributeError('backwards compatibility test')
        self.mock(checkin, 'nologUpdateSrc', attrErrorRaise)
        self.mock(checkin, 'updateSrc',
            lambda *args: mockedFunction(None, savedArgs, None, *args))
        self.assertEquals(None, facade.updateCheckout('targetDirName'))
        self.assertEquals(savedArgs, [('r', [
            os.sep.join((os.getcwd(), 'targetDirName'))])])

        def CheckinErrorRaise(*args):
            raise builderrors.CheckinError()
        self.mock(checkin, 'nologUpdateSrc', CheckinErrorRaise)
        error = self.assertRaises(errors.RbuildError, facade.updateCheckout,
                'targetDirName')
        self.assertEquals(builderrors.CheckinError.__doc__, error.msg)

    def testGetCheckoutStatus(self):
        _, facade = self.prep()
        mock.mockMethod(facade._getRepositoryClient)
        facade._getRepositoryClient._mock.setDefaultReturn('r')
        mockedGenerateStatus = mock.MockObject()
        mockedGenerateStatus._mock.setDefaultReturn(['asdf'])
        self.mock(checkin, 'generateStatus', mockedGenerateStatus)
        ret = facade.getCheckoutStatus('targetDirName')
        mockedGenerateStatus._mock.assertCalled('r', dirName='targetDirName')
        assert ret == ['asdf']

    def testGetCheckoutLog(self):
        _, facade = self.prep()
        repos, sourceState = self.prepReposState(facade)
        sourceState.getName._mock.setDefaultReturn('name')
        mock.mockMethod(facade._getRepositoryVersions)
        mock.mockMethod(facade._getNewerRepositoryVersions)
        facade._getRepositoryVersions._mock.setDefaultReturn(['1'])
        facade._getNewerRepositoryVersions._mock.setDefaultReturn(['broken'])
        flavor = mock.MockObject()
        flavor._mock.setDefaultReturn(flavor)
        self.mock(deps, 'Flavor', flavor)
        trove = mock.MockObject()
        repos.getTroves._mock.setReturn(trove, [('name', '1', flavor)])
        mockedIterLogMessages = mock.MockObject()
        mockedIterLogMessages._mock.setDefaultReturn(['asdf'])
        self.mock(checkin, 'iterLogMessages', mockedIterLogMessages)
        ret = facade.getCheckoutLog('targetDirName')
        mockedIterLogMessages._mock.assertCalled(trove)
        self.assertEquals(ret, ['asdf'])

        facade._getNewerRepositoryVersions._mock.setDefaultReturn(['1'])
        facade._getRepositoryVersions._mock.setDefaultReturn(['broken'])
        ret = facade.getCheckoutLog('dir2', newerOnly=True)
        mockedIterLogMessages._mock.assertCalled(trove)
        self.assertEquals(ret, ['asdf'])

        mock.mock(facade, '_getVersion')
        facade._getVersion._mock.setReturn('1', 'string')
        ret = facade.getCheckoutLog('dir3', versionList=['string'])
        mockedIterLogMessages._mock.assertCalled(trove)
        self.assertEquals(ret, ['asdf'])

    def testIterRepositoryDiff(self):
        _, facade = self.prep()
        repos, sourceState = self.prepReposState(facade)
        ver = mock.MockObject()
        lastver = mock.MockObject()
        sourceState.getName._mock.setDefaultReturn('name')
        sourceState.getVersion._mock.setDefaultReturn(ver)
        mock.mockMethod(facade._getNewerRepositoryVersions)
        facade._getNewerRepositoryVersions._mock.setDefaultReturn(['broken'])
        mock.mock(facade, '_getVersion')
        facade._getVersion._mock.setReturn(lastver, lastver)
        mockedGetIterRdiff = mock.MockObject()
        mockedGetIterRdiff._mock.setDefaultReturn(['asdf'])
        self.mock(checkin, '_getIterRdiff', mockedGetIterRdiff)
        output = [x for x in facade.iterRepositoryDiff('targetDirName',
                                                       lastver=lastver)]
        mockedGetIterRdiff._mock.assertCalled(repos, ver.branch().label(),
            'name', ver.asString(), lastver.asString())
        self.assertEquals(output, ['asdf'])

        facade._getNewerRepositoryVersions._mock.setDefaultReturn(
            [None, None, None, lastver])
        output = [x for x in facade.iterRepositoryDiff('targetDirName')]
        mockedGetIterRdiff._mock.assertCalled(repos, ver.branch().label(),
            'name', ver.asString(), lastver.asString())
        self.assertEquals(output, ['asdf'])

    def testIterCheckoutDiff(self):
        _, facade = self.prep()
        repos, sourceState = self.prepReposState(facade)
        mockedIterDiff = mock.MockObject()
        self.mock(checkin, '_getIterDiff', mockedIterDiff)

        sourceState.getVersion().asString._mock.setDefaultReturn('1')
        mockedIterDiff._mock.setReturn(['asdf'], repos, '1',
            pathList=None, logErrors=False, dirName='.')
        output = [x for x in facade.iterCheckoutDiff('.')]
        self.assertEquals(output, ['asdf'])

        sourceState.getVersion().asString._mock.setDefaultReturn('2')
        mockedIterDiff._mock.setReturn(0, repos, '2',
            pathList=None, logErrors=False, dirName='.')
        output = [x for x in facade.iterCheckoutDiff('.')]
        self.assertEquals(output, [])

        sourceState.getVersion().asString._mock.setDefaultReturn('3')
        mockedIterDiff._mock.setReturn(2, repos, '3',
            pathList=None, logErrors=False, dirName='.')
        output = [x for x in facade.iterCheckoutDiff('.')]
        self.assertEquals(output, [])

    def testGetNewerRepositoryVersionStrings(self):
        _, facade = self.prep()
        mock.mockMethod(facade._getNewerRepositoryVersions)
        facade._getNewerRepositoryVersions._mock.setReturn([1], '.')
        mock.mock(facade, '_versionToString')
        facade._versionToString._mock.setReturn('1', 1)
        output = [x for x in facade._getNewerRepositoryVersionStrings('.')]
        self.assertEquals(output, ['1'])

    def testGetNewerRepositoryVersions(self):
        _, facade = self.prep()
        repos, sourceState = self.prepReposState(facade)
        sourceState.getVersion._mock.setDefaultReturn(1)
        ver0 = mock.MockObject()
        ver1 = mock.MockObject()
        ver2 = mock.MockObject()
        ver0.isAfter._mock.setReturn(False, 1)
        ver1.isAfter._mock.setReturn(False, 1)
        ver2.isAfter._mock.setReturn(True, 1)
        mock.mockMethod(facade._getRepositoryVersions)
        facade._getRepositoryVersions._mock.setDefaultReturn([ver0,ver1,ver2])
        output = facade._getNewerRepositoryVersions('.')
        self.assertEquals(output, [ver2])

    def testGetRepositoryVersions(self):
        _, facade = self.prep()
        repos, sourceState = self.prepReposState(facade)
        sourceState.getBranch._mock.setDefaultReturn('c.r.c@r:2')
        sourceState.getName._mock.setDefaultReturn('asdf')
        repos.getTroveVersionsByBranch._mock.setReturn(
            {'asdf': {1:2, 3:4}}, {'asdf': {'c.r.c@r:2': None}})
        output = facade._getRepositoryVersions('.')
        self.assertEquals(output, [3,1])

        repos.getTroveVersionsByBranch._mock.setReturn(
            None, {'asdf': {'c.r.c@r:2': None}})
        output = facade._getRepositoryVersions('.')
        self.assertEquals(output, [])

    def testGetRepositoryStateFromDirectory(self):
        _, facade = self.prep()
        repos = mock.MockObject()
        mock.mockMethod(facade._getRepositoryClient, repos)
        mock.mock(state, 'ConaryStateFromFile')
        conaryState = mock.MockObject(stableReturnValues=True)
        state.ConaryStateFromFile._mock.setDefaultReturn(conaryState)
        sourceState = conaryState.getSourceState()
        output = facade._getRepositoryStateFromDirectory('.')
        self.assertEquals(output, (repos, sourceState))

    def testIsConaryCheckoutDirectory(self):
        _, facade = self.prep()
        self.mock(os.path, 'exists', lambda *args: True)
        output = facade.isConaryCheckoutDirectory('.')
        self.unmock()
        self.assertEquals(output, True)
        
        self.mock(os.path, 'exists', lambda *args: False)
        output = facade.isConaryCheckoutDirectory('.')
        self.unmock()
        self.assertEquals(output, False)


    def testCreateNewPackage(self):
        _, facade = self.prep()
        mock.mockMethod(facade._getRepositoryClient)
        facade._getRepositoryClient._mock.setDefaultReturn('r')
        mock.mockMethod(facade.getConaryConfig)
        facade.getConaryConfig._mock.setDefaultReturn('c')
        newTrove = mock.MockObject()
        self.mock(checkin, 'newTrove', newTrove)
        facade.createNewPackage('packageName', 'labelName')
        newTrove._mock.assertCalled('r', 'c', 'packageName=labelName',
            dir=None, template=None, factory=None)

    def testCreateNewPackageTemplate(self):
        _, facade = self.prep()
        mock.mockMethod(facade._getRepositoryClient)
        facade._getRepositoryClient._mock.setDefaultReturn('r')
        mock.mockMethod(facade.getConaryConfig)
        facade.getConaryConfig._mock.setDefaultReturn('c')
        newTrove = mock.MockObject()
        self.mock(checkin, 'newTrove', newTrove)
        facade.createNewPackage('packageName', 'labelName',
            template='default')
        newTrove._mock.assertCalled('r', 'c', 'packageName=labelName',
            dir=None, template='default', factory=None)

    def testCreateNewPackageFactory(self):
        _, facade = self.prep()
        mock.mockMethod(facade._getRepositoryClient)
        facade._getRepositoryClient._mock.setDefaultReturn('r')
        mock.mockMethod(facade.getConaryConfig)
        facade.getConaryConfig._mock.setDefaultReturn('c')
        newTrove = mock.MockObject()
        self.mock(checkin, 'newTrove', newTrove)
        facade.createNewPackage('packageName', 'labelName',
            factory='thefact')
        newTrove._mock.assertCalled('r', 'c', 'packageName=labelName',
            dir=None, template=None, factory='thefact')


    def testShadowSource(self):
        _, facade = self.prep()
        troveTup = ('name', 'version', 'targetLabel')
        mock.mock(facade, '_getVersion')
        mock.mock(facade, '_getFlavor')
        mock.mock(facade, '_getLabel')
        mock.mockMethod(facade._getConaryClient)
        facade._getConaryClient._mock.setDefaultReturn(mock.MockObject())

        # First, test the error-return case
        client = facade._getConaryClient()
        client.createShadowChangeSet._mock.setDefaultReturn(None)
        assert facade.shadowSource(*troveTup) == False
        facade._getVersion._mock.assertCalled('version')
        facade._getFlavor._mock.assertCalled()
        facade._getLabel._mock.assertCalled('targetLabel')

        # now test the existing-shadow case
        facade._getConaryClient().createShadowChangeSet._mock.setDefaultReturn(
            ([troveTup], None))
        assert facade.shadowSource(*troveTup) == troveTup

        # finally, test the actually-created-a-shadow case
        cs = mock.MockObject(stableReturnValues=True)
        cs.isEmpty._mock.setDefaultReturn(False)
        trvCs = cs.iterNewTroveList()[0]
        trvCs.getNewNameVersionFlavor._mock.setDefaultReturn(troveTup)
        facade._getConaryClient().createShadowChangeSet._mock.setDefaultReturn(
            (None, cs))
        assert(facade.shadowSource('name', 'version', 'targetLabel') 
                == troveTup)

    def testShadowSourceForBinary(self):
        _, facade = self.prep()
        name, version, flavor = self.makeTroveTuple('foo[ssl]')
        targetLabel = 'localhost@rpl:1'
        version, flavor = str(version), str(flavor)
        client = mock.MockObject()
        mock.mockMethod(facade._getConaryClient, client)
        existingTroves = [self.makeTroveTuple('foo:source')]
        cs = mock.MockObject(iterNewTroveList=lambda: [])
        client.createShadowChangeSet._mock.setDefaultReturn((existingTroves,
                                                             cs))
        results = facade.shadowSourceForBinary(name, version, flavor,
                                               targetLabel)
        trv = existingTroves[0]
        assert(results == (trv[0], str(trv[1]), str(trv[2])))

        facade._getConaryClient().createShadowChangeSet._mock.setDefaultReturn(
                                                                        None)
        results = facade.shadowSourceForBinary(name, version, flavor,
                                               targetLabel)
        assert(results == False)


    def testCheckoutBinaryPackage(self):
        _, facade = self.prep()
        mock.mock(facade, '_getVersion')
        mock.mock(facade, '_getFlavor')
        mockConaryCfg = mock.MockObject()
        mockConaryCfg._mock.enable('root')
        mock.mockMethod(facade.getConaryConfig)
        facade.getConaryConfig._mock.setDefaultReturn(mockConaryCfg)

        # quiet
        savedArgs = []
        doUpdateFn = lambda *args, **kwargs: mockedFunction(None, savedArgs,
                                                        None, *args, **kwargs)
        self.mock(updatecmd, 'doUpdate', doUpdateFn)
        facade.checkoutBinaryPackage('packageName', 'packageVersion',
            'packageFlavor', 'targetDir')
        assert mockConaryCfg.root == 'targetDir'
        assert savedArgs == [(mockConaryCfg,
                             'packageName=packageVersion[packageFlavor]')]

        # noisy
        savedArgs = []
        facade.checkoutBinaryPackage('packageName', 'packageVersion',
            'packageFlavor', 'targetDir', quiet=False)
        assert savedArgs == [(mockConaryCfg,
                             'packageName=packageVersion[packageFlavor]')]


    def testFindPackageInSearchPaths(self):
        _, facade = self.prep()
        repos = mock.MockObject()
        mock.mockMethod(facade._getRepositoryClient, repos)
        groupSpecFoo = ('group-foo', 'localhost@rpl:1', deps.parseFlavor(''))
        groupSpecBar = ('group-bar', 'localhost@rpl:1', deps.parseFlavor(''))
        groupTup = self.makeTroveTuple('group-foo=localhost@rpl:1/1:1.0-1-1')
        groupTup2 = self.makeTroveTuple(
                            'group-foo=localhost@rpl:1/2:2.0-2-1[is:x86]')
        groupTupBar = self.makeTroveTuple(
                            'group-bar=localhost@rpl:1/3:1.0-1-1')
        groupTrv = mock.MockObject(stableReturnValues=True)

        repos.findTroves._mock.setReturn({groupSpecFoo : [groupTup, groupTup2],
                                          groupSpecBar : [groupTupBar]},
                                         None, [groupSpecFoo],
                                         allowMissing = True)
        repos.getTroves._mock.setReturn([groupTrv], 
                                        [groupTup2], withFiles=False)
        iterator = mock.MockObject()
        fooTup = self.makeTroveTuple('foo')
        iterator._mock._dict[0] = fooTup
        iterator._mock._dict[1] = self.makeTroveTuple('blah')
        groupTrv.iterTroveList._mock.setDefaultReturn(iterator)
        self.assertEquals(facade._findPackageInSearchPaths([groupSpecFoo], 'foo'),
                          [fooTup])

        # when no groups are found, return nothing
        repos.findTroves._mock.setReturn({}, None, [groupSpecFoo],
                                         allowMissing = True)
        self.assertEquals(facade._findPackageInSearchPaths([groupSpecFoo], 'foo'),
                          [])

    def testFindPackageInSearchPathsWithLabels(self):
        _, facade = self.prep()
        repos = mock.MockObject()
        mock.mockMethod(facade._getRepositoryClient, repos)
        groupSpecFoo = ('group-foo', 'localhost@rpl:1', deps.parseFlavor(''))
        labelSpecFoo = (None, 'localhost@rpl:2', deps.parseFlavor(''))
        troveSpecFoo = ('foo', ) + labelSpecFoo[1:]

        groupTup = self.makeTroveTuple('group-foo=localhost@rpl:1/1:1.0-1-1')
        groupTup2 = self.makeTroveTuple(
                            'group-foo=localhost@rpl:1/2:2.0-2-1[is:x86]')
        fooTroveTups = [ self.makeTroveTuple(x)
            for x in ['foo=localhost@rpl:2/1:1-1-1[is:x86_64]',
                      'foo=localhost@rpl:2/2:2-1-1[is:x86]']
        ]
        groupTrv = mock.MockObject(stableReturnValues=True)
        groupBarTrv = mock.MockObject(stableReturnValues=True)

        repos.findTroves._mock.setReturn({groupSpecFoo : [groupTup, groupTup2],
                                          troveSpecFoo : fooTroveTups },
                                     None, [groupSpecFoo, troveSpecFoo],
                                     allowMissing = True)
        repos.getTroves._mock.setReturn([groupTrv],
                                        [groupTup2], withFiles=False)
        iterator = mock.MockObject()
        fooTup = self.makeTroveTuple('foo')
        iterator._mock._dict[0] = fooTup
        iterator._mock._dict[1] = self.makeTroveTuple('blah')
        groupTrv.iterTroveList._mock.setDefaultReturn(iterator)
        self.assertEquals(facade._findPackageInSearchPaths(
            [groupSpecFoo, labelSpecFoo], 'foo'), [fooTup, fooTroveTups[1]])

        # when no groups are found, return just the data in the label search
        # path
        repos.findTroves._mock.setReturn({troveSpecFoo : fooTroveTups},
                None, [groupSpecFoo, troveSpecFoo], allowMissing = True)
        self.assertEquals(facade._findPackageInSearchPaths(
            [groupSpecFoo, labelSpecFoo], 'foo'), [fooTroveTups[1]])

    def test_overrideFlavors(self):
        _, facade = self.prep()
        self.assertEquals(facade._overrideFlavors('!foo is:x86',
                                                  ['foo', 'bar']),
                          ['foo is: x86', 'bar,!foo is: x86'])


    def testLoadRecipeClassFromCheckout(self):
        _, facade = self.prep()
        repos = mock.MockObject()
        mock.mockMethod(facade._getRepositoryClient, repos)
        mock.mockMethod(facade.getConaryConfig)
        mock.mock(state, 'ConaryStateFromFile')
        mock.mock(loadrecipe, 'RecipeLoader')
        loader = mock.MockObject()
        loadrecipe.RecipeLoader._mock.setDefaultReturn(loader)
        loader.getRecipe._mock.setDefaultReturn('recipe')
        result = facade._loadRecipeClassFromCheckout(
                                            self.workDir + '/foo.recipe')
        self.assertEquals(result, 'recipe')



    def testRemoveNonRecipeFilesFromCheckout(self):
        handle, facade = self.prep()
        repos = mock.MockObject()
        mock.mockMethod(facade._getRepositoryClient, repos)
        mock.mock(state, 'ConaryStateFromFile')
        conaryState = mock.MockObject(stableReturnValues=True)
        state.ConaryStateFromFile._mock.setDefaultReturn(conaryState)
        sourceState = conaryState.getSourceState()
        iterator = sourceState.iterFileList()
        iterator._mock.setList([('pathId', 'foo.recipe', 'fileId', 'version'),
                                ('pathId2', 'bam', 'fileId', 'version'),
                                ('pathId3', 'directory', 'fileId', 'version')])
        os.mkdir(self.workDir + '/foo')
        os.mkdir(self.workDir + '/foo/directory')
        self.writeFile(self.workDir + '/foo/foo.recipe', 'recipe')
        self.writeFile(self.workDir + '/foo/bam', 'otherfile')
        facade._removeNonRecipeFilesFromCheckout(
                                        self.workDir + '/foo/foo.recipe')
        conaryState.write._mock.assertCalled(self.workDir + '/foo/CONARY')
        sourceState.removeFile._mock.assertCalled('pathId2')
        sourceState.removeFile._mock.assertCalled('pathId3')
        assert(sorted(os.listdir(self.workDir + '/foo')) == ['foo.recipe'])

        # one more time, this time raising error on attempt to unlink
        mock.mock(os, 'unlink')
        os.unlink._mock.raiseErrorOnAccess(OSError('foo', 'bar'))
        self.writeFile(self.workDir + '/foo/bam', 'otherfile')
        facade._removeNonRecipeFilesFromCheckout(
                                        self.workDir + '/foo/foo.recipe')
        handle.ui.warning._mock.assertCalled(
            'cannot remove %s: %s', '%s/foo/bam' % self.workDir, 'bar')

    def testGetFlavorArch(self):
        _, facade = self.prep()
        assert(facade._getFlavorArch('foo,bar is:x86(~i686)') ==  'x86')
        assert(facade._getFlavorArch('foo,bar is:x86(~i686) x86_64') \
                                    == 'x86_64')
        assert(facade._getFlavorArch('foo,bar') == None)

    def testGetShortFlavorDescriptors(self):
        _, facade = self.prep()
        results = facade._getShortFlavorDescriptors(['foo is:x86', 
                                                     'bar is:x86'])
        assert (results == {'foo is: x86' : 'x86-foo',
                            'bar is: x86' : 'x86-bar'})

        # test short-circuit case
        results = facade._getShortFlavorDescriptors([])
        self.failUnlessEqual(results, {})

    def testGetNameForCheckout(self):
        _, facade = self.prep()
        repos = mock.MockObject()
        mock.mockMethod(facade._getRepositoryClient, repos)
        mock.mock(state, 'ConaryStateFromFile')
        conaryState = mock.MockObject(stableReturnValues=True)
        state.ConaryStateFromFile._mock.setDefaultReturn(conaryState)
        sourceState = conaryState.getSourceState()
        sourceState.getName._mock.setReturn('foo:source')
        assert(facade.getNameForCheckout('bam') == 'foo')

    def testIsGroupName(self):
        _, facade = self.prep()
        assert(facade.isGroupName('group-foo'))
        assert(not facade.isGroupName('group-bar:debuginfo'))

    def testPromoteGroups(self):
        _, facade = self.prep()
        client = mock.MockObject()
        mock.mockMethod(facade._getConaryClient, client)
        success = True
        cs = mock.MockObject()
        groupList = [('group-dist', '/localhost@rpl:devel/1.0-1-1', '')],
        trv = mock.MockObject()
        trv.getNewNameVersionFlavor._mock.setReturn(
                        ('group-dist', VFS('/localhost@rpl:qa/1.0-1-1'), ''))
        cs.iterNewTroveList()._mock.setList([trv])
        client.createSiblingCloneChangeSet._mock.setReturn((success, cs),
                {Label('localhost@rpl:devel'): Label('localhost@rpl:qa'),
                 Label('other@somewhere:else'): Label('localhost@rpl:qa'),
                 Label('yetanother@somewhere:else'): VFS('/localhost@rpl:qa')},
                groupList, cloneSources=True)
        mock.mockMethod(facade._getRepositoryClient)
        repos = facade._getRepositoryClient()
        rc = facade.promoteGroups(groupList,
            {'localhost@rpl:devel': 'localhost@rpl:qa',
             'other@somewhere:else': facade._getLabel('localhost@rpl:qa'),
             'yetanother@somewhere:else': '/localhost@rpl:qa'}) # RBLD-91
        assert(rc == [('group-dist', '/localhost@rpl:qa/1.0-1-1', '')])
        repos.commitChangeSet._mock.assertCalled(cs)
        # failureCase
        success = False
        client.createSiblingCloneChangeSet._mock.setReturn((success, None),
                {Label('localhost@rpl:devel'): Label('localhost@rpl:qa')},
                groupList, cloneSources=True)
        err = self.assertRaises(errors.RbuildError,
                                facade.promoteGroups, groupList,
                                {'localhost@rpl:devel': 'localhost@rpl:qa'})
        assert(str(err) == 'Promote failed.')

    def testLatestPackages(self):
        _, facade = self.prep()
        client = mock.MockObject()
        mock.mockMethod(facade._getConaryClient, client)
        client.getRepos().getTroveLatestByLabel._mock.setReturn(
            {'foo': {'foover': ['flav1', 'flav2']},
             'foo:runtime': {'foover': ['flav1', 'flav2']},
             'bar': {'barver': ['flav3']},
             'group-baz': {'bazver': ['flav4']},
             },
            {None: {versions.Label('localhost@rpl:devel'): [None]}})

        # Defaults
        packages = facade.getLatestPackagesOnLabel('localhost@rpl:devel')
        self.failUnlessEqual(sorted(packages), [
            ('bar', 'barver', 'flav3'),
            ('foo', 'foover', 'flav1'),
            ('foo', 'foover', 'flav2'),
          ])

        # With components
        packages = facade.getLatestPackagesOnLabel('localhost@rpl:devel',
            keepComponents=True)
        self.failUnlessEqual(sorted(packages), [
            ('bar', 'barver', 'flav3'),
            ('foo', 'foover', 'flav1'),
            ('foo', 'foover', 'flav2'),
            ('foo:runtime', 'foover', 'flav1'),
            ('foo:runtime', 'foover', 'flav2'),
          ])

        # With groups
        packages = facade.getLatestPackagesOnLabel('localhost@rpl:devel',
            keepGroups=True)
        self.failUnlessEqual(sorted(packages), [
            ('bar', 'barver', 'flav3'),
            ('foo', 'foover', 'flav1'),
            ('foo', 'foover', 'flav2'),
            ('group-baz', 'bazver', 'flav4'),
          ])

    def testFlavorNames(self):
        handle, facade = self.prep()

        # test prefers vs. requires
        flvs = ('~flv1 is: x86', 'flv1 is: x86')
        res = facade._getShortFlavorDescriptors(flvs)
        self.assertEquals(res, {'flv1 is: x86': 'flv1 is: x86',
                                '~flv1 is: x86': '~flv1 is: x86'})

        # test prefers not vs requires not
        flvs = ('~!flv1 is: x86(test)', '!flv1 is: x86(test)', 'is: x86')
        res = facade._getShortFlavorDescriptors(flvs)
        self.assertEquals(res, {'~!flv1 is: x86(test)': '~!flv1 is: x86',
                                '!flv1 is: x86(test)': '!flv1 is: x86',
                                'is: x86': 'is: x86'})

        # this worked all along
        flvs = ('flv1, flv2 is: x86', 'flv1 is: x86')
        res = facade._getShortFlavorDescriptors(flvs)
        self.assertEquals(res, {'flv1,flv2 is: x86': 'x86-flv2',
                                'flv1 is: x86': 'x86'})

        # this mixed flavors
        flvs = ('flv1, flv2 is: x86', '~flv1, !flv2 is: x86')
        res = facade._getShortFlavorDescriptors(flvs)
        self.assertEquals(res, {'flv1,flv2 is: x86': 'x86-flv2',
                                '~flv1,!flv2 is: x86': 'x86'})

    def testGetAllLabelsFromTroves(self):
        handle, facade = self.prep()

        mock.mock(facade, '_findTrovesFlattened')
        specs = [('group-foo-appliance', 'foo@foo:foo', None)]
        tups = [('group-foo-appliance', '/foo@foo:foo/1.2-3-4', 'is: x86')]
        facade._findTrovesFlattened._mock.setReturn(tups, specs)

        subTups = [mock.MockObject(), mock.MockObject()]
        subTups[0][1].trailingLabel().asString._mock.setReturn('foo@foo:foo-bar')
        subTups[1][1].trailingLabel().asString._mock.setReturn('foo@foo:foo-baz')
        troves = [mock.MockObject()]
        troves[0].iterTroveList._mock.setReturn(subTups,
                strongRefs=True, weakRefs=True)
        troves[0].getVersion().trailingLabel().asString._mock.setReturn('foo@foo:foo')

        mock.mock(facade, '_getRepositoryClient')
        facade._getRepositoryClient().getTroves._mock.setReturn(troves, tups,
                withFiles=False)

        self.assertEquals(facade.getAllLabelsFromTroves(specs),
                set(['foo@foo:foo', 'foo@foo:foo-bar', 'foo@foo:foo-baz']))


class QuietUpdateTest(rbuildhelp.RbuildHelper):
    def testQuietUpdateCallback(self):
        callback = conaryfacade._QuietUpdateCallback()
        callback.setUpdateJob()



