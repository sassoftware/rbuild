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


"""
rBuilder facade module

This module provides a high-level stable API for use within rbuild
plugins.  It provides public methods which are only to be accessed
via C{handle.facade.rbuilder} which is automatically available to
all plugins through the C{handle} object.
"""
import os
import re
import time
import socket
import random
import urllib
import urllib2
import urlparse

import robj
from xobj import xobj

from conary.lib import util
from conary.lib.cfg import ConfigFile

from rpath_proddef import api1 as proddef
from rbuild import constants
from rbuild import errors
from rbuild import facade


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
        self.server = facade.ServerProxy(rpcUrl, username=user, password=pw,
                allow_none=True)

    def _pollBuild(self, buildId, interval=10, max_dropped=3):
        dropped = 0
        buildStatus = None
        while buildStatus is None:
            try:
                error, buildStatus = self.server.getBuildStatus(buildId)
            except socket.timeout:
                dropped += 1
                if dropped >= max_dropped:
                    raise errors.RbuildError(
                        'rBuilder connection timed out after 3 attempts')
                self._handle.ui.info(
                    'Status request timed out, trying again')
                time.sleep(interval)
                continue

        if error:
            raise errors.RbuilderError(*buildStatus)
        return buildStatus

    def getBranchIdFromName(self, productName, versionName):
        #pylint: disable-msg=R0914
        # not a great candidate for refactoring
        productId = self.getProductId(productName)
        error, versionList = self.server.getProductVersionListForProduct(
                                                                    productId)
        if error:
            raise errors.RbuilderError(*versionList)

        versionNames = []
        # W0612: leave unused variables as documentation
        # W0631: versionId is guaranteed to be defined
        #pylint: disable-msg=W0612,W0631
        for (versionId2, productId2,
             namespace, versionName2, desc)  in versionList:
            versionNames.append(versionName2)
            if versionName == versionName2:
                return versionId2

        errstr = '%s is not a valid version for product %s.' % \
            (versionName, productName)
        if versionNames:
            errstr += '\nValid versions are: %s' % \
                ', '.join(versionNames)
        else:
            errstr += '\nNo versions found for product %s.' % productName
        raise errors.RbuildError(errstr)

    def getProductLabelFromNameAndVersion(self, productName, versionName):
        versionId = self.getBranchIdFromName(productName, versionName)
        error, stream = self.server.getProductDefinitionForVersion(versionId)
        if error:
            raise errors.RbuilderError(*stream)
        product = proddef.ProductDefinition(stream)
        return product.getProductDefinitionLabel()

    def startProductBuilds(self, productName, versionName, stageName,
            buildNames=None, groupSpecs=None, groupVersion=None):
        versionId = self.getBranchIdFromName(productName, versionName)
        methodArgs = [versionId, stageName, False, buildNames ]
        if groupSpecs is not None:
            # image builds from system model was added later (Sept # 2013),
            # and it causes tracebacks on older rbuilders; only supply
            # it if really needed
            methodArgs.extend([None, groupSpecs])
        elif groupVersion is not None:
            methodArgs.append(groupVersion)

        error, buildIds = self.server.newBuildsFromProductDefinition(
                *methodArgs)
        if error:
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
        if any(x['status'] != 300 for x in finalStatus.values()):
            return False
        else:
            return True

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

    def checkAuth(self):
        error, result = self.server.checkAuth()
        if error:
            raise errors.RbuilderError(*result)
        return result

    def showImageStatus(self, buildIds):
        for buildId in buildIds:
            buildStatus = self._pollBuild(buildId)
            self._handle.ui.write(
                '%s: %s "%s"',
                buildId,
                self.statusNames.get(
                    buildStatus['status'],
                    self.statusNames[-1],
                    ),
                buildStatus['message'],
                )

# For backwards compatibility, rbuilder-client used it (SUP-2356)
RbuilderClient = RbuilderRPCClient


class RbuilderRESTClient(_AbstractRbuilderClient):
    """
    REST rBuilder Client. This will replace the RPC client as more
    functionality is moved into the REST interface.
    """
    _singleBackslashRe = re.compile(r'\\')

    def __init__(self, rbuilderUrl, user, pw, handle):
        _AbstractRbuilderClient.__init__(self, rbuilderUrl, user, pw, handle)
        scheme, _, _, host, port, path, _, _ = util.urlSplit(rbuilderUrl)
        path = util.joinPaths(path, 'api')
        self._url = util.urlUnsplit(
                (scheme, user, pw, host, port, path, None, None))
        self._api = None

    def _getResources(self, resource, **kwargs):
        '''
            Get a fitlered and ordered list of resoruces

            @param resource: resource collection name
            @param order_by: field and direction to order results
            @param uri: alternative uri
            @return: list of resources
            @rtype: list
        '''
        uri = kwargs.pop('uri', None)
        order_by = kwargs.pop('order_by', None)

        fullUri = self.api._uri + '/'
        if uri is not None:
            fullUri += uri.strip('/') + '/'
        fullUri += resource

        filter_by = []
        for field, param in kwargs.items():
            param = self._singleBackslashRe.sub('r\\\\', param)
            param = param.replace('"', r'\"')
            filter_by.append('EQUAL(%s,"%s")' % (field, param))

        if filter_by:
            fullUri += ';filter_by=AND(%s)' % ','.join(filter_by)

        # always sort by most recently created first
        if order_by:
            fullUri += ';order_by=%s' % order_by

        client = self.api._client
        try:
            results = client.do_GET(fullUri)
            if results:
                return results
            return []
        except robj.errors.HTTPNotFoundError:
            raise errors.RbuildError("Unable to fetch resource '%s' at '%s'" %
                                     (resource, fullUri))

    @property
    def api(self):
        if self._api is None:
            top = robj.connect(self._url)
            for ver in top.api_versions:
                if ver.name == 'v1':
                    break
            else:
                raise errors.RbuildError("No compatible REST API found on "
                        "rBuilder '%s'" % self._url.__safe_str__())
            self._api = ver
        return self._api

    def createTarget(self, ddata, ttype):
        '''
        Create a target using the descriptor data provided

        @param ddata: descriptor data for target
        @type: DescriptorData
        @param ttype: target type
        @type ttype: string
        @return: the created Target
        @rtype: robj.HTTPData
        '''
        # Construct the target xml
        target_doc = xobj.Document()
        target_doc.target = target = xobj.XObj()
        target.description = ddata.getField('description')
        target.name = ddata.getField('name')
        target.zone_name = ddata.getField('zone')
        target.target_type_name = ttype.name

        try:
            target = self.api.targets.append(target_doc, tag='target')
        except robj.errors.HTTPConflictError:
            raise errors.RbuildError(
                "A target with conflicting parameters already exists")
        return target

    def configureTarget(self, target, ddata):
        '''
        Configure a target

        @param ddata: descriptor for target
        @type ddata: DescriptorData
        @param target: target to configure
        @type target: rObj(target)
        @return: the configured target
        @rtype: rObj(target)
        '''
        # make sure our target object is up to date
        target.refresh()

        doc = xobj.Document()
        doc.job = job = xobj.XObj()

        job.job_type = target.actions[0]._root.job_type
        job.descriptor = target.actions[0]._root.descriptor
        job.descriptor_data = xobj.parse(ddata.toxml()).descriptor_data

        jobObj = target.jobs.append(doc)
        while jobObj.job_state.name in ['Queued', 'Running']:
            jobObj.refresh()

        if jobObj.job_state.name == 'Failed':
            raise errors.RbuildError(jobObj.status_text)
        return target

    def configureTargetCredentials(self, target, ddata):
        '''
        Configure credentials for a target

        @param ddata: descriptor for target
        @type ddata: DescriptorData
        @param target: target to configure
        @type target: rObj(target)
        @return: the configured target
        @rtype: rObj(target)
        '''
        # make sure our target object is up to date
        target.refresh()

        doc = xobj.Document()
        doc.job = job = xobj.XObj()
        job.job_type = target.actions[1]._root.job_type
        job.descriptor = target.actions[1]._root.descriptor
        job.descriptor_data = xobj.parse(ddata.toxml()).descriptor_data

        jobObj = target.jobs.append(doc)
        while jobObj.job_state.name in ['Queued', 'Running']:
            jobObj.refresh()

        if jobObj.job_state.name == 'Failed':
            raise errors.RbuildError('Unable to set credentials')
        return target

    def getGroups(self, shortName, label, **kwargs):
        client = self.api._client
        uri = ('/products/%s/repos/search?type=group&amp;label=%s' %
               (shortName, label))
        try:
            groups = client.do_GET(uri)
            if groups:
                return groups
            return []
        except robj.errors.HTTPNotFoundError:
            raise errors.RbuildError(
                "Project '%s' and label '%s' not found" % (shortName, label))

    def getImageDefDescriptor(self, imageType):
        # image_type_definition_descriptors are not in a collection, and they
        # have an xml header, which causes rObj to process them incorrectly
        # thus this mess
        client = self.api._client._client  # Ew
        uri = self.api._uri + \
            '/platforms/image_type_definition_descriptors/' + imageType

        request = client.do_GET(uri)
        request.wait()
        response = request.response
        if response.status >= 400:
            raise errors.RbuildError(response.reason)
        return response.content

    def getImages(self, *args, **kwargs):
        '''
            Get a list images. The images returned can be filtered by
            keyword arguments matching the API fields.

            @return: image or None
            @rtype: rObj(image)
        '''
        # for backwards compatibility, we accept image
        # name as a positional arguement
        if args:
            kwargs['name'] = args[0]

        # for backwards compatibility, we transform the
        # keyword 'trailingVersion' into 'trailing_version'
        if 'trailingVersion' in kwargs:
            kwargs['trailing_version'] = kwargs.pop('trailingVersion')

        # default ordering is by creation time, newest first
        if 'order_by' not in kwargs:
            kwargs['order_by'] = '-time_created'

        project = kwargs.pop('project', None)
        branch = kwargs.pop('branch', None)
        stage = kwargs.pop('stage', None)

        # we only support stage filter if we also got a project and branch
        if stage and not (project and branch):
            raise errors.RbuildError(
                'Must provide project and branch if stage is provided')

        if project:
            # use the images resource on the project or stage
            uri = '/projects/' + project
            if stage:
                uri += '/project_branches/' + branch + \
                    '/project_branch_stages/' + stage
            return self._getResources('images', uri=uri, **kwargs)
        return self._getResources('images', **kwargs)

    def getImageDefs(self, product, version, **kwargs):
        # image defs are on the old api, so we have to construct our own url
        client = self.api._client

        uri = ('/products/%s/versions/%s/imageDefinitions' %
               (product, version))
        try:
            availableImageDefs = client.do_GET(uri)
        except robj.errors.HTTPNotFoundError:
            raise errors.RbuildError(
                "Project '%s' and version '%s' not found" % (product, version))

        imageDefs = []
        if availableImageDefs:
            for imageDef in availableImageDefs:
                add = True
                for key, value in kwargs.items():
                    if key == 'id':
                        add = (value == imageDef.id.rsplit('/')[-1])
                    else:
                        add = (getattr(imageDef, key) == value)
                if add:
                    imageDefs.append(imageDef)
        return imageDefs

    def getImageTypes(self, *args, **kwargs):
        return self._getResources("image_types", **kwargs)

    def getImageTypeDef(self, product, version, imageType, arch):
        client = self.api._client
        uri = ('/products/%s/versions/%s/imageTypeDefinitions' %
               (product, version))
        try:
            for imageTypeDef in client.do_GET(uri):
                if (imageTypeDef.container.name == imageType
                        and imageTypeDef.architecture.name == arch):
                    return imageTypeDef
        except robj.errors.HTTPNotFoundError:
            raise errors.RbuildError(
                "Project '%s' and version '%s' not found" % (product, version))

        raise errors.RbuildError("No image type definition with name '%s'"
                                 " and architecture '%s'" % (imageType, arch))

    def getTarget(self, name):
        client = self.api._client
        uri = self.api._uri + '/targets'
        uri += ';filter_by=[name,EQUAL,%s]' % (name,)

        targets = client.do_GET(uri)
        if targets:
            return targets[0]
        raise errors.RbuildError("Target '%s' not found" % (name,))

    def getTargetTypes(self, **kwargs):
        return self._getResources("target_types", **kwargs)

    def getTargets(self, **kwargs):
        '''
        Get all configured targets

        @return: list of configured targets
        @rtype: list of rObj(target)
        '''
        return self._getResources('targets', **kwargs)

    def getUsers(self, **kwargs):
        '''
        Get a filtered list of users

        @return: list of users
        @rtype: list of rObj(user)
        '''
        return self._getResources('users', **kwargs)

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
        raise errors.RbuildError("Unable to determine the product definition "
                "version offered by rBuilder")

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

    def createProject(self, title, shortName, hostName=None, domainName=None,
            description='', external=False, external_params=None):
        assert((external and external_params is not None)
               or (not external and external_params is None))

        doc = xobj.Document()
        doc.project = proj = xobj.XObj()
        proj.name = title
        proj.short_name = shortName
        proj.hostname = hostName or shortName
        proj.description = description or ''
        if domainName:
            proj.domain_name = domainName

        if external:
            proj.external = 'true'
            (proj.labels, proj.upstream_url, proj.auth_type, proj.user_name,
             proj.password, proj.entitlement) = external_params
        else:
            proj.external = 'false'
        try:
            return self.api.projects.append(doc).project_id
        except robj.errors.HTTPConflictError:
            raise errors.RbuildError("A project with conflicting "
                    "parameters already exists")

    def getProject(self, shortName):
        # FIXME: robj allows neither URL construction nor searching/filtering,
        # so the only "kosher" way to find a project is to iterate over all of
        # them. So cheating looks attractive by comparison...
        client = self.api._client
        uri = self.api._uri + '/projects/' + shortName
        try:
            return client.do_GET(uri)
        except robj.errors.HTTPNotFoundError:
            raise errors.RbuildError("Project '%s' not found" % (shortName,))

    def createBranch(self, project, name, platformLabel, namespace=None,
            description=''):
        project = self.getProject(project)
        if project.project_branches and \
                name in [b.name for b in project.project_branches]:
            raise errors.RbuildError("Branch named '%s' already exists" % name)
        doc = xobj.Document()
        doc.project_branch = br = xobj.XObj()
        br.project = xobj.XObj()
        # Why?
        for key in ('id', 'name', 'short_name', 'domain_name'):
            setattr(br.project, key, getattr(project, key))

        br.name = name
        br.platform_label = unicode(platformLabel)
        br.description = description
        if namespace:
            br.namespace = namespace
        try:
            br = project.project_branches.append(doc)
        except robj.errors.HTTPConflictError:
            raise errors.RbuildError("Branch named '%s' already exists" % name)
        return br.label

    def listPlatforms(self):
        ret = []
        for platform in self.api.platforms.platform:
            if platform.enabled.lower() == 'false':
                continue
            if platform.hidden.lower() == 'true':
                continue
            if platform.abstract.lower() == 'true':
                continue
            ret.append(platform)
        return ret


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

    def buildAllImagesForStage(self, buildNames=None, groupSpecs=None,
                               groupVersion=None):
        client = self._getRbuilderRPCClient()
        stageName = self._handle.productStore.getActiveStageName()
        productName = str(self._handle.product.getProductShortname())
        versionName = str(self._handle.product.getProductVersion())
        if groupVersion is not None:
            label = self._handle.product.getLabelForStage(stageName)
            groups = self.getGroups(productName, label)
            for group in groups:
                if group.trailingVersion == groupVersion:
                    break
            else:
                raise errors.BadParameterError("No group matching version: %s" %
                                               groupVersion)
            groupVersion = "%s/%s" % (label, groupVersion)
        buildIds = client.startProductBuilds(productName, versionName,
                stageName, buildNames=buildNames, groupSpecs=groupSpecs,
                groupVersion=groupVersion)
        return buildIds

    def configureTarget(self, target, ddata):
        '''
        Configure a target

        @param ddata: descriptor for target
        @type ddata: DescriptorData
        @param target: target to configure
        @type target: rObj(target)
        @return: the configured target
        @rtype: rObj(target)
        '''
        client = self._getRbuilderRESTClient()
        return client.configureTarget(target, ddata)

    def configureTargetCredentials(self, target, ddata):
        '''
        Configure credentials for a target

        @param ddata: descriptor for target
        @type ddata: DescriptorData
        @param target: target to configure
        @type target: rObj(target)
        @return: the configured target
        @rtype: rObj(target)
        '''
        client = self._getRbuilderRESTClient()
        return client.configureTargetCredentials(target, ddata)

    def createTarget(self, ddata, ttype):
        '''
        Create and configure a target using the descriptor data provided

        @param ddata: descriptor data for target
        @type: DescriptorData
        @param ttype: target type
        @type ttype: string
        @return: the created Target
        @rtype: robj.HTTPData
        '''
        import epdb; epdb.st()  # XXX breakpoint
        client = self._getRbuilderRESTClient()
        return client.createTarget(ddata, ttype)

    def getGroups(self, shortName, label, **kwargs):
        return self._getRbuilderRESTClient().getGroups(shortName, label,
            **kwargs)

    def getImageTypeDef(self, imageType, arch):
        client = self._getRbuilderRESTClient()
        product = self._handle.product.getProductShortname()
        version = self._handle.product.getProductVersion()
        return client.getImageTypeDef(product, version, imageType, arch)

    def getPlatform(self, label):
        client = self._getRbuilderRESTClient()
        for platform in client.api.platforms:
            if platform.label == label:
                return platform

    def getPlatforms(self):
        return self._getRbuilderRESTClient().api.platforms

    def getProductLabelFromNameAndVersion(self, productName, versionName):
        client = self._getRbuilderRPCClient()
        return client.getProductLabelFromNameAndVersion(productName,
                                                        versionName)

    def getProjects(self, **kwargs):
        '''
            Get a list projects. The projects returned can be filtered by
            keyword arguments matching the API fields.

            @return: project or None
            @rtype: rObj(project)
        '''
        client = self._getRbuilderRESTClient()
        return client._getResources('projects', **kwargs)

    def getProjectBranches(self, *args, **kwargs):
        '''
            Get a list of branches for a project
        '''
        try:
            project = kwargs.pop('project', args[0])
        except IndexError:
            raise TypeError("Required argument 'project' (pos 1) noti found")
        order_by = kwargs.pop('order_by', None)

        # name might be a label
        shortName, _, domainName = project.partition('.')
        project = self.getProject(shortName)

        # if the user gave us full repo hostname make
        # sure they gave us the right one
        if (domainName and project.domain_name != domainName):
            raise errors.RbuildError(
                "could not find a project matching '%s'" %
                '.'.join((shortName, domainName)))

        if order_by:
            reverse = (order_by[0] == '-')
            if order_by[0] in ('-', '+'):
                order_by = order_by[1:]
            return sorted(
                project.project_branches,
                key=lambda b: getattr(b, order_by),
                reverse=reverse,
                )
        else:
            return project.project_branches

    def watchImages(self, buildIds, timeout=0, interval = 5, quiet = False):
        client = self._getRbuilderRPCClient()
        return client.watchImages(buildIds, timeout=timeout, interval=interval,
                quiet=quiet)

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

    def getBuildFiles(self, buildId):
        return self._getRbuilderRPCClient().getBuildFiles(buildId)

    def getProductDefinitionSchemaVersion(self):
        client = self._getRbuilderRESTClient()
        return client.getProductDefinitionSchemaVersion()

    def getWindowsBuildService(self):
        client = self._getRbuilderRESTClient()
        return client.getWindowsBuildService()

    def createProject(self, title, shortName, hostName=None, domainName=None,
            description='', external=False, external_params=None):
        if not self.isValidShortName(shortName):
            raise errors.BadParameterError("Invalid project short name")
        if hostName and not self.isValidShortName(hostName):
            raise errors.BadParameterError("Invalid project hostname")
        if not self.isValidDomainName(domainName):
            raise errors.BadParameterError("Invalid project domain name")
        if external and not self._handle.facade.conary.isValidLabel(
                external_params[0][0]):
            raise errors.BadParameterError("Invalid upstream label")
        if (external and external_params[1]
                and not self.isValidUrl(external_params[1])):
            raise errors.BadParameterError("Invalid upstream url")
        client = self._getRbuilderRESTClient()
        return client.createProject(title, shortName, hostName, domainName,
                description, external, external_params)

    def getProject(self, shortName):
        client = self._getRbuilderRESTClient()
        return client.getProject(shortName)

    def createBranch(self, project, name, platformLabel, namespace=None,
            description=''):
        if not self.isValidBranchName(name):
            raise errors.BadParameterError("Invalid branch name")
        client = self._getRbuilderRESTClient()
        return client.createBranch(project, name, platformLabel, namespace,
                description)

    @staticmethod
    def isValidShortName(value):
        return (value and len(value) < 63
            and re.match('^[a-zA-Z][a-zA-Z0-9\-]*$', value))

    @staticmethod
    def isValidDomainName(value):
        return not value or re.match(r'^([a-zA-Z][a-zA-Z0-9\-]*\.)*'
                '[a-zA-Z][a-zA-Z0-9\-]*$', value)

    @staticmethod
    def isValidBranchName(value):
        return value and re.match(r'^[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)*$', value)

    @staticmethod
    def isValidUrl(value):
        try:
            urllib2.urlopen(value).read(1024)
            #pylint: disable-msg=W0703
            # * catch Exception is safe: it displays error to user
        except urllib2.HTTPError as e:
            if e.code != 401:
                return False
        except Exception:
            return False
        return True

    def isAdmin(self, userName=None):
        '''
        Check if the user is an rbuilder administrator. If `user` is None,
        checks if the rbuild user is an admin

        @param userName: user name
        @type userName: str or None
        @return: True if the user is an admin, otherwise False
        @rtype: bool
        '''
        client = self._getRbuilderRESTClient()
        if userName is None:
            userName = self._handle.getConfig().user[0]

        user = client.getUsers(user_name=userName)
        if user:
            return user[0].is_admin == 'true'
        return False

    def listPlatforms(self):
        client = self._getRbuilderRESTClient()
        return client.listPlatforms()

    def getEnabledTargets(self):
        '''
        Get configured targets with valid credentials

        @return: list of targets
        @rtype: list of rObj(target)
        '''
        return [x for x in self.getTargets()
                if x.is_configured == 'true'
                and x.credentials_valid == 'true']

    def getImages(self, *args, **kwargs):
        client = self._getRbuilderRESTClient()
        return client.getImages(*args, **kwargs)

    def getImageDefs(self, *args, **kwargs):
        client = self._getRbuilderRESTClient()
        return client.getImageDefs(*args, **kwargs)

    def getImageDefDescriptor(self, imageType):
        client = self._getRbuilderRESTClient()
        return client.getImageDefDescriptor(imageType)

    def getTargetDescriptor(self, targetType):
        client = self._getRbuilderRESTClient()
        return client.getTargetDescriptor(targetType)

    def getImageTypes(self, *args, **kwargs):
        client = self._getRbuilderRESTClient()
        return client.getImageTypes(*args, **kwargs)

    def getTarget(self, name):
        '''
        Get a target object by name

        @param name: name of target
        @type name: str
        @return: target or None
        @rtype: rObj(target)
        '''
        client = self._getRbuilderRESTClient()
        return client.getTarget(name)

    def getTargets(self, **kwargs):
        '''
        Get all targets

        @return: list of targets
        @rtype: list of rObj
        '''
        client = self._getRbuilderRESTClient()
        return client.getTargets(**kwargs)

    def getTargetTypes(self):
        return self._getRbuilderRESTClient().getTargetTypes()

    def getUsers(self, **kwargs):
        return self._getRbuilderRESTClient().getUsers(**kwargs)

    def showImageStatus(self, buildIds):
        return self._getRbuilderRPCClient().showImageStatus(buildIds)
