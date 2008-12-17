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
rBuilder facade module

This module provides a high-level stable API for use within rbuild
plugins.  It provides public methods which are only to be accessed
via C{handle.facade.rbuilder} which is automatically available to
all plugins through the C{handle} object.
"""
import urllib2
import socket

from conary.conaryclient import cmdline as conarycmdline
from conary.deps import deps as conarydeps
from conary.lib import log
from conary.lib import util

from rpath_common import proddef
from rbuild import errors
from rbuild import facade

import time

class RbuilderFacade(object):
    """
    The rBuild rBuilder facade.

    Note that the contents of objects marked as B{opaque} may vary
    according to the version of rMake and conary in use, and the contents
    of such objecst are not included in the stable rBuild API.
    """

    def __init__(self, handle):
        """
        @param handle: The handle with which this instance is associated.
        """
        self._handle = handle
        self._rbuilderClient = None

    def _getRbuilderClient(self):
        cfg = self._handle.getConfig()
        return RbuilderClient(cfg.serverUrl, cfg.user[0], cfg.user[1])

    def buildAllImagesForStage(self):
        client = self._getRbuilderClient()
        stageName = self._handle.productStore.getActiveStageName()
        productName = str(self._handle.product.getProductShortname())
        versionName = str(self._handle.product.getProductVersion())
        buildIds = client.startProductBuilds(productName, versionName,
                                             stageName)
        return buildIds

    def getProductLabelFromNameAndVersion(self, productName, versionName):
        client = self._getRbuilderClient()
        return client.getProductLabelFromNameAndVersion(productName,
                                                        versionName)

    def watchImages(self, buildIds, timeout=0, interval = 5, quiet = False):
        client = self._getRbuilderClient()
        client.watchImages(buildIds, timeout=timeout, interval=interval, quiet=quiet)

    def validateUrl(self, serverUrl):
        try:
            urllib2.urlopen(serverUrl).read(1024)
            #pylint: disable-msg=W0703
            # * catch Exception is safe: it displays error to user
        except Exception, err:
            self._handle.ui.write('Error contacting \'%s\': %s', serverUrl, err)
            return False
        return True

    def getBuildFiles(self, buildId):
        return self._getRbuilderClient().getBuildFiles(buildId)

    def createRelease(self, buildIds):
        client = self._getRbuilderClient()
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
        client = self._getRbuilderClient()
        return client.updateRelease(releaseId, kwargs)

    def publishRelease(self, releaseId, shouldMirror):
        client = self._getRbuilderClient()
        return client.publishRelease(releaseId, shouldMirror)

class RbuilderClient(object):
    def __init__(self, rbuilderUrl, user, pw):
        self.rbuilderUrl = rbuilderUrl
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
                raise errors.RbuildError('%s\n\nTo submit the partial set of builds, re-run this command with --force' % errFlavors)
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
                        raise errors.RbuildError("Connection timed out (3 attempts)")
                    print 'Status request timed out, trying again'
                    time.sleep(interval)
                    continue

                if error:
                    raise errors.RbuilderError(*buildStatus)
                dropped = 0
                if activeBuilds[buildId] != buildStatus:
                    st = time.time() # reset timeout counter if status changes
                    activeBuilds[buildId] = buildStatus
                    if not quiet:
                        print '%s: %s "%s"' % (buildId, self.statusNames.get(buildStatus['status'], self.statusNames[-1]), buildStatus['message'])
                    if activeBuilds[buildId]['status'] > 200:
                        finalStatus[buildId] = activeBuilds.pop(buildId)
            if activeBuilds:
                time.sleep(interval)
                if timeout and time.time() - st > timeout:
                    timedOut = True
                    break

        if timedOut:
            print "Time out while waiting for build status to change (%d seconds)" % timeout
            print
        else:
            print "All jobs completed"
            print
        if activeBuilds:
            print "Unfinished builds:"
            self._printStatus(activeBuilds, '    Last status: ')
        print "Finished builds:"
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
            print "%sBuild %d ended with '%s' status: %s" % (prefix, buildId,
                self.statusNames.get(statusDict[buildId]['status'], self.statusNames[-1]), statusDict[buildId]['message'])

    def getBuildFiles(self, buildId):
        error, filenames = self.server.getBuildFilenames(buildId)
        if error:
            raise errors.RbuilderError(*filenames)
        for bf in filenames:
            if 'size' in bf:
                #Workaround for marshalling size over int32 based xml-rpc
                bf['size'] = int(bf['size'])

        # extract the downloadImage url from the serverUrl configuration
        parts = list(urllib2.urlparse.urlparse(self.rbuilderUrl))
        parts[1] = urllib2.splituser(parts[1])[1]
        parts[2] = parts[2] and parts[2] or '/'

        LOCAL                   = 0
        AMAZONS3                = 1
        AMAZONS3TORRENT         = 2
        GENERICMIRROR           = 999

        for filename in filenames:
            for urlId, urlType, url in filename['fileUrls']:
                if urlType == AMAZONS3TORRENT:
                    urlBase = "http://%s%s/downloadTorrent?fileId=%%d" % \
                        (parts[1], util.normpath(parts[2] + "../")[1:])
                else:
                    urlBase = "http://%s%s/downloadImage?fileId=%%d" % \
                        (parts[1], util.normpath(parts[2] + "../")[1:])
                print urlBase % (filename['fileId'])



    def getProductId(self, productName):
        error, productId = self.server.getProjectIdByHostname(productName)
        if error:
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
