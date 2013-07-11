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
import robj
import socket
import time
import urllib2
from collections import namedtuple
from rpath_proddef import api1 as proddef
from StringIO import StringIO

from rbuild import errors
from rbuild import facade as fac_mod
from rbuild.facade import rbuilderfacade
from rbuild_test import rbuildhelp
from testutils import mock


class RbuilderConfigTest(rbuildhelp.RbuildHelper):
    def test_rBuilderConfig(self):
        oldHome = os.environ['HOME']
        try:
            os.environ['HOME'] = self.workDir
            rbcfg = rbuilderfacade._rBuilderConfig()
            self.assertEquals(rbcfg.serverUrl, None)
            serverUrl = 'https://user:password@host/path'
            file(self.workDir + '/.rbuilderrc', 'w+').write(
                'serverUrl %s\n' %serverUrl)
            rbcfg = rbuilderfacade._rBuilderConfig()
            self.assertEquals(rbcfg.serverUrl, serverUrl)
        finally:
            os.environ['HOME'] = oldHome


class RbuilderFacadeTest(rbuildhelp.RbuildHelper):
    def prep(self):
        handle = mock.MockObject()
        cfg = mock.MockObject(serverUrl = 'http://localhost',
                              user=('foo', 'bar'))
        handle.getConfig._mock.setReturn(cfg)
        handle.productStore.getActiveStageName._mock.setReturn('devel')
        facade = rbuilderfacade.RbuilderFacade(handle)

        return handle, facade

    def test_getRbuilderClient(self):
        _, facade = self.prep()
        mockClass = mock.MockObject()
        facade._getRbuilderClient(mockClass)
        mockClass._mock.assertCalled('http://localhost', 'foo', 'bar',
                                     facade._handle)

    def test_getRbuilderClientDefault(self):
        _, facade = self.prep()
        mock.mock(rbuilderfacade, 'RbuilderRPCClient')
        facade._getRbuilderClient()
        rbuilderfacade.RbuilderRPCClient._mock.assertCalled('http://localhost',
                                                         'foo', 'bar',
                                                         facade._handle)
    def test_getRbuilderRPCClient(self):
        _, facade = self.prep()
        mock.mock(rbuilderfacade, 'RbuilderRPCClient')
        facade._getRbuilderRPCClient()
        rbuilderfacade.RbuilderRPCClient._mock.assertCalled('http://localhost',
                                                         'foo', 'bar',
                                                         facade._handle)

    def test_getRbuilderRESTClient(self):
        _, facade = self.prep()
        mock.mock(rbuilderfacade, 'RbuilderRESTClient')
        facade._getRbuilderRESTClient()
        rbuilderfacade.RbuilderRESTClient._mock.assertCalled(
            'http://localhost', 'foo', 'bar', facade._handle)

    def test_getBaseServerUrl(self):
        _, facade = self.prep()
        rbcfg = mock.MockObject()
        rbcfg._mock.enable('serverUrl')
        rbcfg.serverUrl = None
        def _rBuilderConfig():
            return rbcfg
        self.mock(rbuilderfacade, '_rBuilderConfig', _rBuilderConfig)
        self.assertEquals(facade._getBaseServerUrl(), None)
        serverUrl = 'https://user:password@host/path'
        rbcfg.serverUrl = serverUrl
        self.assertEquals(facade._getBaseServerUrl(), serverUrl)

    def test_getBaseServerUrlData(self):
        _, facade = self.prep()
        mock.mockMethod(facade._getBaseServerUrl)
        facade._getBaseServerUrl._mock.setDefaultReturn(None)
        self.assertEquals(facade._getBaseServerUrlData(),
                          (None, None, None))
        serverUrl = 'https://user:password@host/path'
        facade._getBaseServerUrl._mock.setDefaultReturn(serverUrl)
        self.assertEquals(facade._getBaseServerUrlData(),
                          ('https://host/path', 'user', 'password'))
        serverUrl = 'https://user@host/path'
        facade._getBaseServerUrl._mock.setDefaultReturn(serverUrl)
        self.assertEquals(facade._getBaseServerUrlData(),
                          ('https://host/path', 'user', None))
        serverUrl = 'https://host/path'
        facade._getBaseServerUrl._mock.setDefaultReturn(serverUrl)
        self.assertEquals(facade._getBaseServerUrlData(),
                          ('https://host/path', None, None))


    def testBuildAllImagesForStage(self):
        handle, facade = self.prep()
        handle.product.getProductShortname._mock.setReturn('shortname')
        handle.product.getProductVersion._mock.setReturn('1.0')
        mock.mockMethod(facade._getRbuilderRPCClient)
        client = facade._getRbuilderRPCClient()
        client.startProductBuilds._mock.setReturn([1],
                                                  'shortname', '1.0', 'devel')
        buildIds = facade.buildAllImagesForStage()
        assert(buildIds == [1])


    def testWatchImages(self):
        _, facade = self.prep()
        mock.mockMethod(facade._getRbuilderRPCClient)
        facade.watchImages([1])
        facade._getRbuilderRPCClient().watchImages._mock.assertCalled([1], interval=5, quiet=False, timeout=0)

    def testGetBuildFiles(self):
        _, facade = self.prep()
        mock.mockMethod(facade._getRbuilderRPCClient)
        facade.getBuildFiles(1)
        facade._getRbuilderRPCClient().getBuildFiles._mock.assertCalled(1)

    def testGetProductLabelFromNameAndVersion(self):
        _, facade = self.prep()
        mock.mockMethod(facade._getRbuilderRPCClient)
        facade.getProductLabelFromNameAndVersion('foo', '1')
        facade._getRbuilderRPCClient().getProductLabelFromNameAndVersion._mock.assertCalled('foo', '1')

    def testCheckForRmake(self):
        _, facade = self.prep()
        mock.mock(socket, 'socket')
        ret = facade.checkForRmake('http://localhost')
        socket.socket().connect._mock.assertCalled(('localhost', 9999))
        socket.socket().close._mock.assertCalled()
        self.assertEquals(ret, True)
        ret = facade.checkForRmake('localhost')
        self.assertEquals(ret, False)
        socket.socket().connect._mock.raiseErrorOnAccess(socket.error)
        ret = facade.checkForRmake('http://localhost')
        self.assertEquals(ret, False)

    def testValidateUrl(self):
        mock.mock(urllib2, 'urlopen')
        connection = mock.MockObject()
        urllib2.urlopen._mock.setReturn(connection, 'http://foo/conaryrc')
        connection.read._mock.setReturn('data', 1024)
        handle, facade = self.prep()
        assert(facade.validateUrl('http://foo') is True)
        connection.read._mock.assertCalled(1024)
        err = RuntimeError('foo')
        connection.read._mock.raiseErrorOnAccess(err)
        assert(facade.validateUrl('http://foo') is False)
        handle.ui.writeError._mock.assertCalled("Error contacting '%s': %s", 'http://foo', err)

    def testValidateRbuilderUrl(self):
        handle, facade = self.prep()
        mock.mock(rbuilderfacade, 'RbuilderRPCClient')
        rbuilderfacade.RbuilderRPCClient().checkAuth._mock.setDefaultReturn(dict(authorized=True))
        rbuilderfacade.RbuilderRPCClient._mock.popCall()
        ret = facade.validateRbuilderUrl('http://foo')
        self.assertEquals(rbuilderfacade.RbuilderRPCClient._mock.popCall(),
                          (('http://foo', '', '', handle), ()))
        assert((True, '')==ret)
        e = Exception()
        rbuilderfacade.RbuilderRPCClient().checkAuth._mock.raiseErrorOnAccess(e)
        ret = facade.validateRbuilderUrl('http://foo')
        assert((False, e)==ret)

    def testValidateCredentials(self):
        handle, facade = self.prep()
        mock.mock(rbuilderfacade, 'RbuilderRPCClient')
        rbuilderfacade.RbuilderRPCClient().checkAuth._mock.setDefaultReturn(dict(authorized=True))
        rbuilderfacade.RbuilderRPCClient._mock.popCall()
        auth = facade.validateCredentials('user', 'pass', 'http://foo')
        assert(auth is True)
        self.assertEquals(rbuilderfacade.RbuilderRPCClient._mock.popCall(),
                          (('http://foo', 'user', 'pass', handle), ()))
        rbuilderfacade.RbuilderRPCClient().checkAuth._mock.setDefaultReturn(dict())
        auth = facade.validateCredentials('user', 'pass', 'http://foo')
        assert(auth is False)

    def testGetProjectUrl(self):
        handle, facade = self.prep()
        mock.mockMethod(facade._getBaseServerUrlData)._mock.setDefaultReturn(('asdf', None, None))
        handle.product.getProductShortname._mock.setDefaultReturn('pdct')
        self.assertEquals(facade.getBuildUrl(5), 'asdf/project/pdct/build?id=5')

    def testGetProductDefinitionSchemaVersion(self):
        handle, facade = self.prep()
        mock.mockMethod(facade._getRbuilderRESTClient)
        facade.getProductDefinitionSchemaVersion()
        facade._getRbuilderRESTClient().getProductDefinitionSchemaVersion._mock.assertCalled()

    def testCreateProject(self):
        handle, facade = self.prep()
        mock.mockMethod(facade._getRbuilderRESTClient)
        facade.createProject('title', 'shortname', 'hostname', 'domain.name')
        self.assertRaises(errors.BadParameterError, facade.createProject,
                'title', 'illegal.short')
        self.assertRaises(errors.BadParameterError, facade.createProject,
                'title', 'short', 'illegal.host')
        self.assertRaises(errors.BadParameterError, facade.createProject,
                'title', 'short', None, 'bad.0.domain')

    def testCreateBranch(self):
        handle, facade = self.prep()
        mock.mockMethod(facade._getRbuilderRESTClient)
        facade.createBranch('proj', 'branch', 'plat')
        facade._getRbuilderRESTClient().createBranch._mock.assertCalled(
                'proj', 'branch', 'plat', None, '')
        self.assertRaises(errors.BadParameterError, facade.createBranch,
                'proj', '-1', 'plat')

    def testGetProject(self):
        handle, facade = self.prep()
        mock.mockMethod(facade._getRbuilderRESTClient)
        facade._getRbuilderRESTClient().getProject._mock.setReturn('project', 'shortname')
        self.assertEqual(facade.getProject('shortname'), 'project')

    def testListPlatforms(self):
        handle, facade = self.prep()
        mock.mockMethod(facade._getRbuilderRESTClient)
        facade._getRbuilderRESTClient().listPlatforms._mock.setReturn(['platform'])
        self.assertEqual(facade.listPlatforms(), ['platform'])

    def testGetWindowsBuildService(self):
        handle, facade = self.prep()
        mock.mockMethod(facade._getRbuilderRESTClient)
        facade._getRbuilderRESTClient().getWindowsBuildService._mock.setReturn('rwbs')
        self.assertEqual(facade.getWindowsBuildService(), 'rwbs')


class RbuilderRPCClientTest(rbuildhelp.RbuildHelper):
    def _getClient(self):
        mock.mock(fac_mod, 'ServerProxy')
        return rbuilderfacade.RbuilderRPCClient('http://localhost', 'foo', 'bar',
            mock.MockObject())

    def testRbuilderRPCClientInit(self):
        mock.mock(fac_mod, 'ServerProxy')
        rbuilderfacade.RbuilderRPCClient('http://localhost', 'foo', 'bar', None)
        fac_mod.ServerProxy._mock.assertCalled(
                                'http://localhost/xmlrpc-private', username='foo', password='bar')
        rbuilderfacade.RbuilderRPCClient('https://localhost2', 'foo2', 'bar', None)
        fac_mod.ServerProxy._mock.assertCalled(
                                'https://localhost2/xmlrpc-private', username='foo2', password='bar')

    def testGetProductLabelFromNameAndVersion2(self):
        client = self._getClient()
        server = client.server
        server.getProjectIdByHostname._mock.setReturn((False, 32),
                                                       'foo.rpath.org')
        productVersionList = [(1, 32, 'rpl', '1.0', 'version 1.0'),
                              (2, 32, 'rpl', '2.0', 'version 2.0')]
        returnValue = (False, productVersionList)
        server.getProductVersionListForProduct._mock.setReturn(returnValue, 32)
        server.getProductDefinitionForVersion._mock.setReturn(
                                                    (False, 'stream'), 1)
        mock.mock(proddef, 'ProductDefinition')
        product = mock.MockObject()
        proddef.ProductDefinition._mock.setReturn(product, 'stream')
        product.getProductDefinitionLabel._mock.setReturn(
                                                        'foo.rpath.org@rpl:1')
        rc = client.getProductLabelFromNameAndVersion('foo.rpath.org', '1.0')
        assert(rc == 'foo.rpath.org@rpl:1')
        err = self.assertRaises(errors.RbuildError,
                    client.getProductLabelFromNameAndVersion, 
                    'foo.rpath.org', '3.0')
        self.assertEquals(str(err), '3.0 is not a valid version for product '
            'foo.rpath.org.\nValid versions are: 1.0, 2.0')
        server.getProductVersionListForProduct._mock.setReturn((False, []), 32)
        err = self.assertRaises(errors.RbuildError,
                    client.getProductLabelFromNameAndVersion, 
                    'foo.rpath.org', '3.0')
        self.assertEquals(str(err), '3.0 is not a valid version for product '
            'foo.rpath.org.\nNo versions found for product foo.rpath.org.')
        server.getProductVersionListForProduct._mock.setReturn(returnValue, 32)
        server.getProductDefinitionForVersion._mock.setReturn(
                (True, ('FooError', '')), 1)
        assertRaiseArgs = (errors.RbuildError,
            client.getProductLabelFromNameAndVersion, 'foo.rpath.org', '1.0')
        err = self.assertRaises(*assertRaiseArgs)
        self.assertEqual(str(err), "rBuilder error FooError: ''")

        server.getProductVersionListForProduct._mock.setReturn(
                (True, ('BarError', '')), 32)
        err = self.assertRaises(*assertRaiseArgs)
        self.assertEqual(str(err), "rBuilder error BarError: ''")

        server.getProjectIdByHostname._mock.setReturn(
                (True, ('BazError', 1337)), 'foo.rpath.org')
        err = self.assertRaises(*assertRaiseArgs)
        self.assertEqual(str(err), "rBuilder error BazError: 1337")

    def testStartProductBuilds(self):
        client = self._getClient()
        server = client.server
        server.getProjectIdByHostname._mock.setReturn((False, 32),
                                                       'foo.rpath.org')
        productVersionList = [(1, 32, 'rpl', '1.0', 'version 1.0'),
                              (2, 32, 'rpl', '2.0', 'version 2.0')]

        oldProductVersionList = [(1, 32, '1.0', 'version 1.0'),
                                 (2, 32, '2.0', 'version 2.0')]
        returnValue = (False, productVersionList)
        server.getProductVersionListForProduct._mock.setReturn(returnValue, 32)
        returnValue = (False, [1, 2, 3, 4, 5])
        server.newBuildsFromProductDefinition._mock.setReturn(returnValue,
                                                              2, 'devel', False)
        buildIds = client.startProductBuilds('foo.rpath.org', '2.0', 'devel')
        assert(buildIds == [1, 2, 3, 4, 5])

        #Test for old productVersionLists
        server.getProductVersionListForProduct._mock.setReturn((False,
                                                oldProductVersionList), 32)
        buildIds = client.startProductBuilds('foo.rpath.org', '2.0', 'devel')
        assert(buildIds == [1, 2, 3, 4, 5])
        
        # now test for error conditions
        server.newBuildsFromProductDefinition._mock.setReturn((True,
                                                    ['ErrorClass', 'message']),
                                                    2, 'devel', False)
        err = self.assertRaises(errors.RbuildError,
                                client.startProductBuilds, 
                                'foo.rpath.org', '2.0', 'devel')
        self.failUnlessEqual(str(err), "rBuilder error ErrorClass: 'message'")
        

        server.newBuildsFromProductDefinition._mock.setReturn((True,
            ['TroveNotFoundForBuildDefinition', [[
            "Trove 'group-dumponme-appliance' has no matching flavors "
            "for '~X,~!alternatives,!bootstrap,!cross,~!dom0,!domU,~vmware"
            ",~!xen,~!xfce is: x86(~cmov,~i486,~i586,~i686,~mmx,~sse,~sse2)'"]]]),
                                    2, 'devel', False)
        err = self.assertRaises(errors.RbuildError,
                                client.startProductBuilds, 
                                'foo.rpath.org', '2.0', 'devel')
        self.assertEquals(err.msg,
            "Trove 'group-dumponme-appliance' has no matching flavors for "
            "'~X,~!alternatives,!bootstrap,!cross,~!dom0,!domU,~vmware,"
            "~!xen,~!xfce is: x86(~cmov,~i486,~i586,~i686,~mmx,~sse,~sse2)'"
            "\n\nTo submit the partial set of builds, re-run this command "
            "with --force")

        productVersionList = [(1, 32, 'rpl', '1.0', 'version 1.0')]
        returnValue = (False, productVersionList)
        server.getProductVersionListForProduct._mock.setReturn(returnValue, 32)

        err = self.assertRaises(errors.RbuildError,
                                client.startProductBuilds, 
                                'foo.rpath.org', '2.0', 'devel')
        assert(str(err) == "could not find version '2.0'"
                           " for product 'foo.rpath.org'")
        server.getProductVersionListForProduct._mock.setReturn(
                                [True, ["ErrorClass2", "Message"]], 32)
        err = self.assertRaises(errors.RbuildError,
                                client.startProductBuilds, 
                                'foo.rpath.org', '2.0', 'devel')
        self.assertEqual(str(err), "rBuilder error ErrorClass2: 'Message'")
        server.getProjectIdByHostname._mock.setReturn(
                                        [True, ["ErrorClass3", "message3"]],
                                        'foo.rpath.org')
        err = self.assertRaises(errors.RbuildError,
                                client.startProductBuilds, 
                                'foo.rpath.org', '2.0', 'devel')
        self.assertEqual(str(err), "rBuilder error ErrorClass3: 'message3'")


    def testWatchImages(self):
        client = self._getClient()
        server = client.server
        mock.mock(time, 'sleep')
        server.getBuildStatus._mock.setReturns(
                            [(False, {'message' : 'foo', 'status' : 0}),
                             (False, {'message' : 'bar', 'status' : 300})],
                                        1)
        server.getBuildStatus._mock.setReturns(
                            [(False, {'message' : 'bam', 'status' : 200}),
                             (False, {'message' : 'zap', 'status' : 500})],
                                        2)
        client.watchImages([1, 2])
        client._handle.ui.info._mock.assertNotCalled()
        client._handle.ui.warning._mock.assertNotCalled()
        client._handle.ui.error._mock.assertNotCalled()
        self.assertEquals(
            [x[0][0]%x[0][1:] for x in client._handle.ui.write._mock.calls],
            ['1: Waiting "foo"',
             '2: Built "bam"',
             '1: Finished "bar"',
             '2: Unknown "zap"',
             'All jobs completed',
             'Finished builds:',
             "    Build 1 ended with 'Finished' status: bar",
             "    Build 2 ended with 'Unknown' status: zap"])

        server.getBuildStatus._mock.setReturns(
                            [(False, {'message' : 'bam', 'status' : 200}),
                             (True, ('Error', ''))], 1)
        err = self.assertRaises(errors.RbuildError, self.captureOutput, 
                                client.watchImages, [1])
        self.assertEqual(str(err), "rBuilder error Error: ''")


    def testWatchImagesSocketTimeout(self):
        client = self._getClient()
        server = client.server
        mock.mock(time, 'sleep')
        import socket
        def foo(*a, **k):
            raise socket.timeout()
        server._mock.set(getBuildStatus=foo)
        err = self.assertRaises(errors.RbuildError, client.watchImages, [1, 2])
        self.assertEquals('rBuilder connection timed out after 3 attempts',
                          err.msg)

    def testWatchImagesStatusTimeout(self):
        client = self._getClient()
        server = client.server
        mock.mock(time, 'sleep')
        self.now = 1000
        def foo():
            self.now += 1
            return self.now
        self.mock(time, 'time', foo)
        server.getBuildStatus._mock.setReturn(
            (False, {'message' : 'bam', 'status' : 200}), 2)
        client.watchImages([2], timeout=30)
        self.assertEquals(
            [x[0][0]%x[0][1:] for x in client._handle.ui.write._mock.calls],
            ['2: Built "bam"',
             "    Last status: Build 2 ended with 'Built' status: bam",
             'Finished builds:'])
        self.assertEquals(
            [x[0][0]%x[0][1:] for x in client._handle.ui.error._mock.calls],
            ['Timed out while waiting for build status to change (30 seconds)'])

    def testGetBuildFiles(self):
        client = self._getClient()
        server = client.server
        server.getBuildFilenames._mock.setReturn( [False,
 [{'downloadUrl': 'http://www.rpath.org/downloadImage?fileId=20588',
   'fileId': 20588,
   'fileUrls': [[40478,
                 1,
                 'http://s3.amazonaws.com/rbuilder/rpath%2F12423%2Frpath-1.0.7-x86-disc1.iso'],
                [40479,
                 2,
                 'http://s3.amazonaws.com/rbuilder/rpath%2F12423%2Frpath-1.0.7-x86-disc1.iso?torrent']],
   'idx': 0,
   'sha1': '511b07104feff5324c8c02321311b576a4af158e',
   'size': '733597696',
   'title': 'rPath Linux Disc 1'},
  {'downloadUrl': 'http://www.rpath.org/downloadImage?fileId=20589',
   'fileId': 20589,
   'fileUrls': [[40480,
                 1,
                 'http://s3.amazonaws.com/rbuilder/rpath%2F12423%2Frpath-1.0.7-x86-disc2.iso'],
                [40481,
                 2,
                 'http://s3.amazonaws.com/rbuilder/rpath%2F12423%2Frpath-1.0.7-x86-disc2.iso?torrent']],
   'idx': 1,
   'sha1': '8a2046e33b039c2136aedc7b2781df17e9789ab4',
   'size': '728041472',
   'title': 'rPath Linux Disc 2'},
  {'downloadUrl': 'http://www.rpath.org/downloadImage?fileId=20590',
   'fileId': 20590,
   'fileUrls': [[40482,
                 1,
                 'http://s3.amazonaws.com/rbuilder/rpath%2F12423%2Fboot.iso'],
                [40483,
                 2,
                 'http://s3.amazonaws.com/rbuilder/rpath%2F12423%2Fboot.iso?torrent']],
   'idx': 2,
   'sha1': '4110078186db232af4d27674f85cd3ecb1322c12',
   'size': '6352896',
   'title': 'boot.iso'},
  {'downloadUrl': 'http://www.rpath.org/downloadImage?fileId=20591',
   'fileId': 20591,
   'fileUrls': [[40484,
                 1,
                 'http://s3.amazonaws.com/rbuilder/rpath%2F12423%2Fdiskboot.img'],
                [40485,
                 2,
                 'http://s3.amazonaws.com/rbuilder/rpath%2F12423%2Fdiskboot.img?torrent']],
   'idx': 3,
   'sha1': '76dca62f95287cfd99ede402625be1be9ba125dd',
   'size': '8388608',
   'title': 'diskboot.img'}]],
                12423
            )
        self.assertEquals(client.getBuildFiles(12423),
            [{'baseFileName': 'rpath-1.0.7-x86-disc1.iso',
              'downloadUrl': 'http://localhost/downloadImage?fileId=20588',
              'fileId': 20588,
              'sha1': '511b07104feff5324c8c02321311b576a4af158e',
              'size': 733597696,
              'title': 'rPath Linux Disc 1',
              'torrentUrl': 'http://localhost/downloadTorrent?fileId=20588'},
             {'baseFileName': 'rpath-1.0.7-x86-disc2.iso',
              'downloadUrl': 'http://localhost/downloadImage?fileId=20589',
              'fileId': 20589,
              'sha1': '8a2046e33b039c2136aedc7b2781df17e9789ab4',
              'size': 728041472,
              'title': 'rPath Linux Disc 2',
              'torrentUrl': 'http://localhost/downloadTorrent?fileId=20589'},
             {'baseFileName': 'boot.iso',
              'downloadUrl': 'http://localhost/downloadImage?fileId=20590',
              'fileId': 20590,
              'sha1': '4110078186db232af4d27674f85cd3ecb1322c12',
              'size': 6352896,
              'title': 'boot.iso',
              'torrentUrl': 'http://localhost/downloadTorrent?fileId=20590'},
             {'baseFileName': 'diskboot.img',
              'downloadUrl': 'http://localhost/downloadImage?fileId=20591',
              'fileId': 20591,
              'sha1': '76dca62f95287cfd99ede402625be1be9ba125dd',
              'size': 8388608,
              'title': 'diskboot.img',
              'torrentUrl': 'http://localhost/downloadTorrent?fileId=20591'}])

        server.getBuildFilenames._mock.setReturn( [True, ('InternalError', 'This error proves the error conditions work')], 12423)
        err = self.assertRaises(errors.RbuildError, client.getBuildFiles, 12423)
        self.assertEquals(err.error, 'InternalError')
        self.assertEquals(err.frozen, 'This error proves the error conditions work')

    def testGetProductId(self):
        client = self._getClient()
        server = client.server
        server.getProjectIdByHostname._mock.setDefaultReturn((False, 42))
        rc = client.getProductId('testproduct')
        assert(rc==42)
    
        server.getProjectIdByHostname._mock.setDefaultReturn((True, (42,'')))
        self.assertRaises(errors.RbuildError, client.getProductId,
            'testproduct')

        server.getProjectIdByHostname._mock.setDefaultReturn(
            (True, ('ItemNotFound',)))
        self.assertRaises(errors.RbuildError, client.getProductId, 
            'testproduct')

    def testCheckAuth(self):
        client = self._getClient()
        server = client.server
        server.checkAuth._mock.setDefaultReturn((False, 1))
        rc = client.checkAuth()
        assert(rc==1)
        server.checkAuth._mock.setDefaultReturn((True, (1, '')))
        self.assertRaises(errors.RbuilderError, client.checkAuth)


class RbuilderRESTClientTest(rbuildhelp.RbuildHelper):
    def setUp(self):
        rbuildhelp.RbuildHelper.setUp(self)

        from rbuild.facade import rbuilderfacade

        mockFinder = mock.MockObject()
        self.mock(rbuilderfacade, 'ApiFinder', mockFinder)

        mockUrl = mock.MockObject()
        mockFinder._mock.setReturn(mockUrl, 'localhost')

        mockUrl3 = mock.MockObject()
        mockUrl3._mock.set(url='http://localhost/api/v1')

        mockUrl2 = mock.MockObject()
        mockUrl2._mock.setReturn(mockUrl3, '')

        mockUrl._mock.set(url=mockUrl2)

    def _getMockResponse(self, content):
        response = StringIO(content)
        return response

    def testAPI(self):
        client = rbuilderfacade.RbuilderRESTClient('http://localhost', 'foo',
            'bar', mock.MockObject())
        self.failUnlessEqual(client._api, None)

        mock.mock(robj, 'connect')
        class v1:
            name = 'v1'
        class v2:
            name = 'v2'
        class top:
            api_versions = [v2]

        robj.connect._mock.setReturn(top, 'http://foo:bar@localhost/api')
        err = self.assertRaises(errors.RbuildError, getattr, client, 'api')
        self.assertEqual(str(err), "No compatible REST API found on rBuilder "
                "'http://foo:<PASSWD>@localhost/api'")
        self.assertEqual(client._api, None)

        top.api_versions.append(v1)
        robj.connect._mock.setReturn(top, 'http://foo:bar@localhost/api')
        api = client.api
        self.failIfEqual(client._api, None)
        self.failUnlessEqual(api, v1)

    def testGetProductDefinitionSchemaVersion(self):
        client = rbuilderfacade.RbuilderRESTClient('http://localhost', 'foo',
            'bar', mock.MockObject())
        client._api = mock.MockObject()

        # no REST api case
        client._api._mock.set(proddefSchemaVersion=None)
        client._api._mock.set(version_info=None)
        result = client.getProductDefinitionSchemaVersion()
        self.failUnlessEqual(result, '2.0')

        # pre 5.2.3 api
        client._api._mock.set(proddefSchemaVersion='2.0')
        client._api._mock.set(version_info=None)
        result = client.getProductDefinitionSchemaVersion()
        self.failUnlessEqual(result, '2.0')

        # 5.2.3 > 6.1.0
        client._api._mock.set(proddefSchemaVersion='3.0')
        client._api._mock.set(version_info=None)
        result = client.getProductDefinitionSchemaVersion()
        self.failUnlessEqual(result, '3.0')

        # 6.1.0 and later
        vinfo = mock.MockObject()
        vinfo._mock.set(product_definition_schema_version='4.3')
        client._api._mock.set(version_info=vinfo)
        client._api._mock.set(proddefSchemaVersion=None)
        result = client.getProductDefinitionSchemaVersion()
        self.failUnlessEqual(result, '4.3')

    def testGetWindowsBuildService(self):
        client = rbuilderfacade.RbuilderRESTClient('http://localhost', 'foo',
            'bar', mock.MockObject())
        mock.mock(client, '_api')
        client._api._mock.set(inventory=mock.MockObject())

        notwbs = mock.MockObject(system_type=mock.MockObject(
            name='foobar'))

        # Correct WBS system.
        wbs = mock.MockObject(system_type=mock.MockObject(
            name='infrastructure-windows-build-node'),
            networks=[mock.MockObject(ip_address='1.2.3.4',
                                      dns_name='foo.example.com'), ])
        client._api.inventory._mock.set(infrastructure_systems=[wbs, notwbs])
        address = client.getWindowsBuildService()
        self.failUnlessEqual(address, '1.2.3.4')

        # No WBS systems found.
        wbs2 = mock.MockObject(system_type=mock.MockObject(name='bar'))
        client._api.inventory._mock.set(infrastructure_systems=[wbs2, notwbs])
        self.failUnlessRaises(errors.RbuildError, client.getWindowsBuildService)

        # Selected WBS system doesn't have any networks.
        wbs3 = mock.MockObject(system_type=mock.MockObject(
            name='infrastructure-windows-build-node'),
            networks=[])
        client._api.inventory._mock.set(infrastructure_systems=[wbs3, notwbs])
        self.failUnlessRaises(errors.RbuildError, client.getWindowsBuildService)

    def testCreateProject(self):
        client = rbuilderfacade.RbuilderRESTClient('http://localhost', 'foo',
            'bar', mock.MockObject())
        mock.mock(client, '_api')
        class response:
            project_id = 42
        client._api.projects.append._mock.setDefaultReturn(response)
        projectId = client.createProject('title', 'shortname', 'hostname', 'domain.name')
        self.assertEqual(projectId, 42)
        proj = client._api.projects.append._mock.popCall()[0][0].project
        self.assertEqual(proj.name, 'title')
        self.assertEqual(proj.hostname, 'hostname')
        self.assertEqual(proj.short_name, 'shortname')
        self.assertEqual(proj.domain_name, 'domain.name')
        self.assertEqual(proj.external, 'false')

        client._api.projects.append._mock.raiseErrorOnAccess(
                robj.errors.HTTPConflictError(uri=None, status=None,
                    reason=None, response=None))
        err = self.assertRaises(errors.RbuildError, client.createProject, 'title', 'shortname', 'hostname', 'domain.name')
        self.assertIn('conflicting', str(err))

    def testGetProject(self):
        client = rbuilderfacade.RbuilderRESTClient('http://localhost', 'foo',
                'bar', mock.MockObject())
        mock.mock(client, '_api')
        client._api._mock.set(_uri='http://localhost')

        client._api._client.do_GET._mock.setReturn('response',
                'http://localhost/projects/foo')
        self.assertEqual(client.getProject('foo'), 'response')

        client._api._client.do_GET._mock.raiseErrorOnAccess(
                robj.errors.HTTPNotFoundError(uri=None, status=None,
                    reason=None, response=None))
        err = self.assertRaises(errors.RbuildError, client.getProject, 'bar')
        self.assertIn('not found', str(err))

    def testCreateBranch(self):
        client = rbuilderfacade.RbuilderRESTClient('http://localhost', 'foo',
            'bar', mock.MockObject())
        mock.mock(client, '_api')
        proj = mock.MockObject()
        proj._mock.set(id='id', name='proj', short_name='short',
                domain_name='dom')
        mock.mockMethod(client.getProject)
        client.getProject._mock.setReturn(proj, 'proj')

        client.createBranch('proj', 'branch', 'plat', 'nsp', 'desc')
        xml = proj.project_branches.append._mock.popCall()[0][0].project_branch
        self.assertEqual(xml.name, 'branch')
        self.assertEqual(xml.platform_label, 'plat')
        self.assertEqual(xml.description, 'desc')
        self.assertEqual(xml.namespace, 'nsp')
        self.assertEqual(xml.project.id, 'id')

    def testListPlatforms(self):
        client = rbuilderfacade.RbuilderRESTClient('http://localhost', 'foo',
            'bar', mock.MockObject())
        mock.mock(client, '_api')
        Platform = namedtuple('Platform',
                'enabled hidden abstract platformName label')
        client._api.platforms._mock.set(platform=[
            Platform('true',  'false', 'false', 'plat1', 'plat@1'),
            Platform('false', 'false', 'false', 'plat2', 'plat@2'),
            Platform('true',  'true',  'false', 'plat3', 'plat@3'),
            Platform('true',  'false', 'true',  'plat4', 'plat@4'),
            ])
        results = client.listPlatforms()
        self.assertEqual(results, [Platform('true', 'false', 'false', 'plat1', 'plat@1')])
