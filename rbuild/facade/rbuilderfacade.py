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

from rpath_common import proddef
from rbuild import errors
from rbuild import facade


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

    def watchImages(self, buildIds):
        client = self._getRbuilderClient()
        client.watchImages(buildIds)

    def validateUrl(self, serverUrl):
        try:
            urllib2.urlopen(serverUrl).read(1024)
            #pylint: disable-msg=W0703
            # * catch Exception is safe: it displays error to user
        except Exception, err:
            self._handle.ui.write('Error contacting \'%s\': %s', serverUrl, err)
            return False
        return True

    def createRelease(self, buildIds):
        client = self._getRbuilderClient()
        product = self._handle.product
        productName = str(product.getProductShortname())
        return client.createRelease(productName, buildIds) 

    def updateRelease(self, releaseId, data):
        client = self._getRbuilderClient()
        return client.updateRelease(releaseId, data)

    def publishRelease(self, releaseId, shouldMirror):
        client = self._getRbuilderClient()
        return client.publishRelease(releaseId, shouldMirror)

class RbuilderClient(object):
    def __init__(self, rbuilderUrl, user, pw):
        rpcUrl = rbuilderUrl + '/xmlrpc-private'
        self.server = facade.ServerProxy(rpcUrl, username=user, password=pw)

    def getProductLabelFromNameAndVersion(self, productName, versionName):
        error, productId = self.server.getProjectIdByHostname(productName)
        if error:
            raise errors.RbuildError(*productId)
        error, versionList = self.server.getProductVersionListForProduct(
                                                                    productId)
        if error:
            raise errors.RbuildError(*versionList)

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
                raise errors.RbuildError(*stream)
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

    def startProductBuilds(self, productName, versionName, stageName):
        error, productId = self.server.getProjectIdByHostname(productName)
        if error:
            raise errors.RbuildError(*productId)
        error, versionList = self.server.getProductVersionListForProduct(
                                                                    productId)
        if error:
            raise errors.RbuildError(*versionList)

        versionId = None
        # W0612: leave unused variables as documentation
        # W0631: versionId is guaranteed to be defined
        #pylint: disable-msg=W0612,W0631
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
                                                versionId, stageName, False)

        if error:
            raise errors.RbuildError(buildIds)
        return buildIds

    def watchImages(self, buildIds):
        import time
        activeBuilds = dict.fromkeys(buildIds)
        while activeBuilds:
            for buildId in list(activeBuilds):
                error, buildStatus = self.server.getBuildStatus(buildId)
                if error:
                    raise errors.RbuildError(buildStatus)
                if activeBuilds[buildId] != buildStatus:
                    activeBuilds[buildId] = buildStatus
                    print '%s: %s' % (buildId, buildStatus['message'])
                    if activeBuilds[buildId]['status'] > 200:
                        del activeBuilds[buildId]
                time.sleep(.5)
            time.sleep(5)

    def getProductId(self, productName):
        error, productId = self.server.getProjectIdByHostname(productName)
        if error:
            raise errors.RbuildError(*productId)
        return productId            

    def createRelease(self, productName, buildIds):
        productId = self.getProductId(productName)
        error, releaseId = self.server.newPublishedRelease(productId)
        if error:
            raise errors.RbuildError(*releaseId)
        for buildId in buildIds:
            error, msg = self.server.setBuildPublished(buildId,
                                                       releaseId, True)
            if error:
                raise errors.RbuildError(*msg)
        return releaseId

    def updateRelease(self, releaseId, data):
        error, result = self.server.updatePublishedRelease(releaseId, data)
        if error:
            raise errors.RbuildError(*result)

    def publishRelease(self, releaseId, shouldMirror):
        error, result = self.server.publishPublishedRelease(releaseId,
            shouldMirror)
        if error:
            raise errors.RbuildError(*result)
        return result

    # disable until writing rbuild publish
    #def publishAndMirror(self, productName, buildIds):
    #    error, productId = self.server.getProjectIdByHostname(productName)
    #    if error:
    #        raise RbuildError(*productId)
    #    error, releaseId = self.server.newPublishedRelease(productId)
    #    if error:
    #        raise RbuildError(*newPublishedRelease)
    #    for buildId in buildIds:
    #        error, msg = self.server.setBuildPublished(buildId, 
    #                                                   releaseId, True)
    #        if error:
    #            raise RbuildError(*msg)
    #    mirror = True
    #    self.server.publishPublishedRelease(self.pubReleaseId, mirror)
