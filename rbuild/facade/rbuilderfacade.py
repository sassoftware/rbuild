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
rBuilder facade module

This module provides a high-level stable API for use within rbuild
plugins.  It provides public methods which are only to be accessed
via C{handle.facade.rbuilder} which is automatically available to
all plugins through the C{handle} object.
"""
import os
import time
import socket
import random
import urllib
import urllib2
import urlparse

import robj

from lxml import etree

from conary.conaryclient import cmdline as conarycmdline
from conary.deps import deps as conarydeps
from conary.lib import log
from conary.lib import util
from conary.lib.cfg import ConfigFile

from rpath_proddef import api1 as proddef
from rbuild import constants
from rbuild import errors
from rbuild import facade
from apifinder import ApiFinder

class _rBuilderConfig(ConfigFile):
    serverUrl = None

    def __init__(self):
        ConfigFile.__init__(self)
        if os.environ.has_key('HOME'):
            fn = '/'.join((os.environ['HOME'], '.rbuilderrc'))
            self.read(fn, exception=False)


class _AbstractRbuilderClient(object):
    """
    Abstract class for both the XMLRPC and REST rBuilder client to
    inherit from.
    """

    def __init__(self, rbuilderUrl, user, pw, handle):
        self.rbuilderUrl = rbuilderUrl
        self._handle = handle


class RbuilderRPCClient(_AbstractRbuilderClient):
    """
    XMLRPC rBuilder Client. As rBuilder moves functionality to the REST
    interface this client will become deprecated.
    """

    def __init__(self, rbuilderUrl, user, pw, handle):
        _AbstractRbuilderClient.__init__(self, rbuilderUrl, user, pw, handle)
        rpcUrl = rbuilderUrl + '/xmlrpc-private'
        self.server = facade.ServerProxy(rpcUrl, username=user, password=pw)

    def getProductLabelFromNameAndVersion(self, productName, versionName):
        #pylint: disable-msg=R0914
        # not a great candidate for refactoring
        productId = self.getProductId(productName)
        error, versionList = self.server.getProductVersionListForProduct(
                                                                    productId)
        if error:
            raise errors.RbuilderError(*versionList)

        versionId = None
        versionNames = []
        # W0612: leave unused variables as documentation
        # W0631: versionId is guaranteed to be defined
        #pylint: disable-msg=W0612,W0631
        for (versionId2, productId2,
             namespace, versionName2, desc)  in versionList:
            versionNames.append(versionName2)
            if versionName == versionName2:
                versionId = versionId2
                break

        if versionId:
            error, stream = self.server.getProductDefinitionForVersion(
                versionId)
            if error:
                raise errors.RbuilderError(*stream)
            product = proddef.ProductDefinition(stream)
            return product.getProductDefinitionLabel()
        else:
            errstr = '%s is not a valid version for product %s.' % \
                (versionName, productName)
            if versionNames:
                errstr += '\nValid versions are: %s' % \
                    ', '.join(versionNames)
            else:
                errstr += '\nNo versions found for product %s.' % productName
            raise errors.RbuildError(errstr)

    def startProductBuilds(self, productName, versionName, stageName, force=False):
        productId = self.getProductId(productName)
        error, versionList = self.server.getProductVersionListForProduct(
                                                                    productId)
        if error:
            raise errors.RbuilderError(*versionList)

        versionId = None
        # W0612: leave unused variables as documentation
        # W0631: versionId is guaranteed to be defined
        #pylint: disable-msg=W0612,W0631
        if versionList:
            if len(versionList[0]) == 4:
                #This is an older rBuilder
                for (versionId2, productId2, versionName2, desc) in versionList:
                    if versionName == versionName2:
                        versionId = versionId2
                        break
            else:
                for (versionId2, productId2,
                     namespace, versionName2, desc)  in versionList:
                    if versionName == versionName2:
                        versionId = versionId2
                        break
        if versionId is None:
            raise errors.RbuildError(
                "could not find version %r for product %r" % (versionName,
                                                              productName))
        error, buildIds = self.server.newBuildsFromProductDefinition(
                                                versionId, stageName, force)

        if error:
            if buildIds[0] == 'TroveNotFoundForBuildDefinition':
                errFlavors = '\n'.join(buildIds[1][0])
                raise errors.RbuildError('%s\n\nTo submit the partial set of '
                    'builds, re-run this command with --force' % errFlavors)
            else:
                raise errors.RbuilderError(*buildIds)
        return buildIds

    def watchImages(self, buildIds, timeout = 0, interval = 5, quiet=False):
        interval = 10
        st = time.time()
        timedOut = False
        dropped = 0
        finalStatus = {}

        activeBuilds = dict.fromkeys(buildIds)
        while activeBuilds:
            for buildId in list(activeBuilds):
                try:
                    error, buildStatus = self.server.getBuildStatus(buildId)
                except socket.timeout:
                    dropped += 1
                    if dropped >= 3:
                        raise errors.RbuildError(
                            'rBuilder connection timed out after 3 attempts')
                    self._handle.ui.info(
                        'Status request timed out, trying again')
                    time.sleep(interval)
                    continue

                if error:
                    raise errors.RbuilderError(*buildStatus)
                dropped = 0
                if activeBuilds[buildId] != buildStatus:
                    st = time.time() # reset timeout counter if status changes
                    activeBuilds[buildId] = buildStatus
                    if not quiet:
                        self._handle.ui.write('%s: %s "%s"',
                            buildId, self.statusNames.get(buildStatus['status'],
                            self.statusNames[-1]), buildStatus['message'])
                    if activeBuilds[buildId]['status'] > 200:
                        finalStatus[buildId] = activeBuilds.pop(buildId)
            if activeBuilds:
                time.sleep(interval)
                if timeout and time.time() - st > timeout:
                    timedOut = True
                    break

        if timedOut:
            self._handle.ui.error('Timed out while waiting for build status'
                ' to change (%d seconds)', timeout)
        else:
            self._handle.ui.write('All jobs completed')
        if activeBuilds:
            self._handle.ui.warning('Unfinished builds:')
            self._printStatus(activeBuilds, '    Last status: ')
        self._handle.ui.write('Finished builds:')
        self._printStatus(finalStatus, '    ')

    statusNames = {
            -1:  'Unknown',
            0:   'Waiting',
            100: 'Running',
            200: 'Built',
            300: 'Finished',
            301: 'Failed',
            302: 'Killed',
            401: 'No job',
        }

    def _printStatus(self, statusDict, prefix = ''):
        for buildId in statusDict.iterkeys():
            self._handle.ui.write("%sBuild %d ended with '%s' status: %s",
                prefix, buildId,
                self.statusNames.get(statusDict[buildId]['status'],
                self.statusNames[-1]), statusDict[buildId]['message'])

    def _getBaseDownloadUrl(self):
        '''
        Return the base URL relative to which to download images,
        removing any user/password information, and using http
        '''
        # extract the downloadImage base url from the serverUrl configuration
        parts = list(urllib2.urlparse.urlparse(self.rbuilderUrl))
        parts[1] = urllib2.splituser(parts[1])[1]
        # FIXME: is this whole ../ business a workaround for splitbrain rBO?
        parts[2] = parts[2] and parts[2] or '/'
        return 'http://%s%s' %(parts[1], util.normpath(parts[2] + '../')[1:])

    def getBuildFiles(self, buildId):
        '''
        Get a list of dicts describing files associated with a build.
        Zero ore more of the following elements may be set in each dict:
        - C{sha1}: (string) SHA1 of the described file
        - C{size}: (int) Length in bytes
        - C{title}: (string) Title describing file (not necessarily file name)
        - C{downloadUrl}: (string) URL to use to download the file directly
        - C{torrentUrl}: (string) URL to use to downlad the file via bittorrent
        - C{baseFileName}: (string) basename of the file 
        - C{fileId}: (int) unique identifier for this file
        Additional items may be set as well.
        @param buildId: unique identifier for a build
        @type buildId: int
        @return: list of dicts
        '''
        error, filenames = self.server.getBuildFilenames(buildId)
        if error:
            raise errors.RbuilderError(*filenames)

        baseUrl = self._getBaseDownloadUrl()

        LOCAL                   = 0
        AMAZONS3                = 1
        AMAZONS3TORRENT         = 2
        GENERICMIRROR           = 999

        buildFileList = []
        for filename in filenames:
            b = dict((x, y) for x, y in filename.iteritems()
                     if x in set(('sha1', 'title', 'fileId')))
            if 'size' in filename:
                # XML-RPC cannot marshal large ints, so size may be string
                b['size'] = int(filename['size'])
            fileId = b['fileId']
            for _, urlType, url in filename['fileUrls']:
                if 'baseFileName' not in b:
                    b['baseFileName'] = os.path.basename(
                        url.replace('%2F', '/'))
                if urlType == AMAZONS3TORRENT:
                    b['torrentUrl'] = '%s/downloadTorrent?fileId=%d' %(
                        baseUrl, fileId)
                else:
                    b['downloadUrl'] = '%s/downloadImage?fileId=%d' %(
                        baseUrl, fileId)
            buildFileList.append(b)

        return buildFileList


    def getProductId(self, productName):
        error, productId = self.server.getProjectIdByHostname(productName)
        if error:
            if productId[0] == 'ItemNotFound':
                raise errors.RbuildError('Product %s not found' % \
                    productName)
            else:
                raise errors.RbuilderError(*productId)
        return productId            

    def createRelease(self, productName, buildIds):
        productId = self.getProductId(productName)
        error, releaseId = self.server.newPublishedRelease(productId)
        if error:
            raise errors.RbuilderError(*releaseId)
        for buildId in buildIds:
            error, msg = self.server.setBuildPublished(buildId,
                                                       releaseId, True)
            if error:
                raise errors.RbuilderError(*msg)
        return releaseId

    def updateRelease(self, releaseId, data):
        error, result = self.server.updatePublishedRelease(releaseId, data)
        if error:
            raise errors.RbuilderError(*result)

    def publishRelease(self, releaseId, shouldMirror):
        error, result = self.server.publishPublishedRelease(releaseId,
            shouldMirror)
        if error:
            raise errors.RbuilderError(*result)
        return result

    def checkAuth(self):
        error, result = self.server.checkAuth()
        if error:
            raise errors.RbuilderError(*result)
        return result

# For backwards compatibility, rbuilder-client used it (SUP-2356)
RbuilderClient = RbuilderRPCClient

class RbuilderRESTClient(_AbstractRbuilderClient):
    """
    REST rBuilder Client. This will replace the RPC client as more
    functionality is moved into the REST interface.
    """

    def __init__(self, rbuilderUrl, user, pw, handle):
        _AbstractRbuilderClient.__init__(self, rbuilderUrl, user, pw, handle)
        scheme, _, _, host, port, path, query, fragment = util.urlSplit(rbuilderUrl)
        self._url = util.urlUnsplit((scheme, user, pw, host, port, path, query, fragment))

        server_port = host
        if port is not None:
            server_port = "%s:%s" % (host, port)
        found = ApiFinder(server_port).url('')
        scheme, _, _, host, port, path, query, fragment = util.urlSplit(found.url)
        self._basePath = path
        self._api = None

    @property
    def api(self):
        if self._api is None:
            uri = urlparse.urljoin(self._url, self._basePath)
            self._api = robj.connect(uri)
        return self._api

    def getProductDefinitionSchemaVersion(self):
        # rBuilder 5.2.3 <= version < rBuilder 6.1.0
        ver = getattr(self.api, 'proddefSchemaVersion', None)
        if ver is not None:
            return str(ver)
        # version >= rBuilder 6.1.0
        version_info = getattr(self.api, 'version_info', None)
        if version_info is not None:
            ver = getattr(version_info, 'product_definition_schema_version',
                    None)
            if ver is not None:
                return str(ver)
        # proddefSchemaVersion was added in rBuilder 5.2.3, prior to that the
        # schema version was 2.0.
        return '2.0'

    def getWindowsBuildService(self):
        systems = self.api.inventory.infrastructure_systems

        wbsSystems = [ x for x in systems
            if x.system_type.name == 'infrastructure-windows-build-node' ]

        if len(wbsSystems) == 0:
            raise errors.RbuildError('Could not find any available Windows '
                'Build Service systems on your rBuilder. A Windows Build '
                'Service is required for building Windows related packages.')

        wbs = random.choice(wbsSystems)

        if len(wbs.networks) == 0:
            raise errors.RbuildError('Could not find any usable networks on '
                'the Windows Build Service.')

        network = wbs.networks[0]
        address = str(network.ip_address) or str(network.dns_name)
        return address


class RbuilderFacade(object):
    """
    The rBuild rBuilder facade.

    Note that the contents of objects marked as B{opaque} may vary
    according to the version of rMake and Conary in use, and the contents
    of such objects are not included in the stable rBuild API.
    """

    def __init__(self, handle):
        """
        @param handle: The handle with which this instance is associated.
        """
        self._handle = handle

    def _getRbuilderClient(self, clientcls=None):
        if clientcls is None:
            clientcls=RbuilderRPCClient
        cfg = self._handle.getConfig()
        return clientcls(cfg.serverUrl, cfg.user[0], cfg.user[1],
                                 self._handle)

    def _getRbuilderRPCClient(self):
        return self._getRbuilderClient(RbuilderRPCClient)

    def _getRbuilderRESTClient(self):
        return self._getRbuilderClient(RbuilderRESTClient)

    def _getBaseServerUrl(self):
        """
        Fetch serverUrl from ~/.rbuilderrc if it exists and is specified
        """
        rbcfg = _rBuilderConfig()
        return rbcfg.serverUrl

    def _getBaseServerUrlData(self):
        """
        Fetch serverUrl from ~/.rbuilderrc if it exists and is specified;
        removes user and password from the URL and returns them separately.
        @return serverUrl, user, password
        """
        serverUrl = self._getBaseServerUrl()
        if not serverUrl:
            return (None, None, None)
        scheme, rest = serverUrl.split(':', 1)
        host = urllib.splithost(rest)[0]
        user = urllib.splituser(host)[0]
        if user:
            user, password = urllib.splitpasswd(user)
        else:
            password = None
        if password:
            serverUrl = serverUrl.replace(':%s' %password, '', 1)
        if user:
            serverUrl = serverUrl.replace('%s@' %user, '', 1)
        return serverUrl, user, password

    def buildAllImagesForStage(self):
        client = self._getRbuilderRPCClient()
        stageName = self._handle.productStore.getActiveStageName()
        productName = str(self._handle.product.getProductShortname())
        versionName = str(self._handle.product.getProductVersion())
        buildIds = client.startProductBuilds(productName, versionName,
                                             stageName)
        return buildIds

    def getProductLabelFromNameAndVersion(self, productName, versionName):
        client = self._getRbuilderRPCClient()
        return client.getProductLabelFromNameAndVersion(productName,
                                                        versionName)

    def watchImages(self, buildIds, timeout=0, interval = 5, quiet = False):
        client = self._getRbuilderRPCClient()
        client.watchImages(buildIds, timeout=timeout, interval=interval, quiet=quiet)

    def checkForRmake(self, serverUrl):
        try:
            url = serverUrl.split('//')[1]
        except IndexError, e:
            return False

        sock = socket.socket()
        try:
            sock.connect((url, constants.RMAKE_PORT))
            sock.close()
            return True
        except socket.error, e:
            return False

    def validateUrl(self, serverUrl):
        try:
            urllib2.urlopen(serverUrl + '/conaryrc').read(1024)
            #pylint: disable-msg=W0703
            # * catch Exception is safe: it displays error to user
        except Exception, err:
            self._handle.ui.writeError('Error contacting \'%s\': %s',
                                       serverUrl, err)
            return False
        return True

    def validateRbuilderUrl(self, serverUrl):
        try:
            client = RbuilderRPCClient(serverUrl, '', '', self._handle)
            client.checkAuth()
        except Exception, err:
            return False, err

        return True, ''

    def validateCredentials(self, username, password, serverUrl):
        client = RbuilderRPCClient(serverUrl, username, password, self._handle)
        try:
            ret = client.checkAuth()
            return ret['authorized']
        except Exception, err:
            return False

    def _getProjectUrl(self, type, id):
        return '%s/project/%s/%s?id=%d' %(
            self._getBaseServerUrlData()[0],
            str(self._handle.product.getProductShortname()),
            type,
            int(id))

    def getBuildUrl(self, buildId):
        return self._getProjectUrl('build', buildId)

    def getReleaseUrl(self, releaseId):
        return self._getProjectUrl('release', releaseId)

    def getBuildFiles(self, buildId):
        return self._getRbuilderRPCClient().getBuildFiles(buildId)

    def createRelease(self, buildIds):
        client = self._getRbuilderRPCClient()
        product = self._handle.product
        productName = str(product.getProductShortname())
        return client.createRelease(productName, buildIds) 

    def updateRelease(self, releaseId, **kwargs):
        '''
        Update release C{releaseId} with rBuilder release information
        dictionary elements passed as keyword arguments.
        Raises C{errors.RbuilderError} particularly if arguments
        have been passed that are not understood by the version of
        rBuilder being contacted.  At least C{name}, C{version},
        and C{description} will be accepted.

        @param releaseId: rBuilder identifier for a release (see C{createRelease})
        @type releaseId: int
        @param kwargs: rBuilder release information dictionary elements
        @type kwargs: dict
        @raise errors.RbuilderError
        '''
        client = self._getRbuilderRPCClient()
        return client.updateRelease(releaseId, kwargs)

    def publishRelease(self, releaseId, shouldMirror):
        client = self._getRbuilderRPCClient()
        return client.publishRelease(releaseId, shouldMirror)

    def getProductDefinitionSchemaVersion(self):
        client = self._getRbuilderRESTClient()
        return client.getProductDefinitionSchemaVersion()

    def getWindowsBuildService(self):
        client = self._getRbuilderRESTClient()
        return client.getWindowsBuildService()
