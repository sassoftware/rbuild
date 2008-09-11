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
rMake facade module

This module provides a high-level stable API for use within rbuild
plugins.  It provides public methods which are only to be accessed
via C{handle.facade.rmake} which is automatically available to
all plugins through the C{handle} object.
"""
import os

from rmake.build import buildcfg
from rmake.cmdline import helper
from rmake.cmdline import query
from rmake import plugins

class RmakeFacade(object):
    """
    The rBuild rMake facade.

    Note that the contents of objects marked as B{opaque} may vary
    according to the version of rMake and conary in use, and the contents
    of such objecst are not included in the stable rBuild API.
    """

    def __init__(self, handle):
        """
        @param handle: The handle with which this instance is associated.
        """
        self._handle = handle
        self._rmakeConfig = None
        self._rmakeConfigWithContexts = None
        self._plugins = None

    def _getRmakeConfig(self, useCache=True):
        """
        Returns an rmake configuration file that matches the product associated
        with the current handle.
        @param useCache: if True, uses a cached version of the rmake
        configuration
        file if available.
        @return: rMake configuration file suitable for use with the current
        product.
        """
        if self._rmakeConfig and useCache:
            return self._rmakeConfig
        conaryFacade = self._handle.facade.conary
        stageName = self._handle.productStore.getActiveStageName()
        stageLabel = conaryFacade._getLabel(
            self._handle.product.getLabelForStage(stageName))
        baseFlavor = conaryFacade._getFlavor(
            self._handle.product.getBaseFlavor())
        rmakeConfigPath = self._handle.productStore.getRmakeConfigPath()

        rbuildConfig = self._handle.getConfig()
        if not self._plugins:
            p = plugins.PluginManager(rbuildConfig.rmakePluginDirs, ['test'])
            p.loadPlugins()
            p.callLibraryHook('library_preInit')
            self._plugins = p


        cfg = buildcfg.BuildConfiguration(False)
        cfg.rbuilderUrl = self._handle.getConfig().serverUrl
        cfg.rmakeUser = self._handle.getConfig().user
        cfg.resolveTrovesOnly = True
        cfg.shortenGroupFlavors = True
        cfg.ignoreExternalRebuildDeps = True
        if self._handle.getConfig().rmakePluginDirs:
            cfg.pluginDirs = self._handle.getConfig().rmakePluginDirs

        cfg.buildLabel = stageLabel
        cfg.installLabelPath = [ stageLabel ]
        cfg.flavor = [baseFlavor]
        cfg.buildFlavor = baseFlavor
        upstreamSources = self._handle.product.getSearchPaths()
        upstreamSources = [(x.troveName, x.label, None)
                            for x in upstreamSources]
        cfg.resolveTroves = [upstreamSources]

        cfg.repositoryMap = rbuildConfig.repositoryMap
        #E1101: Instance of 'BuildConfiguration' has no 'user' member - untrue
        #pylint: disable-msg=E1101
        cfg.user.append((stageLabel.getHost(),) + rbuildConfig.user)
        if rbuildConfig.rmakeUrl:
            cfg.rmakeUrl = rbuildConfig.rmakeUrl
        cfg.rmakeUser = rbuildConfig.user
        cfg.name = rbuildConfig.name
        cfg.contact = rbuildConfig.contact
        self._handle.facade.conary._parseRBuilderConfigFile(cfg)

        if os.path.exists(rmakeConfigPath):
            cfg.includeConfigFile(rmakeConfigPath)

        if useCache:
            self._rmakeConfig = cfg

        return cfg

    def _getRmakeConfigWithContexts(self):
        """
        Returns an rmake configuration file that matches the product associated
        with the current handle.  Beyond the settings provided in 
        _getRmakeConfig, this rmake configuration will have contexts set up 
        that match the flavors required by the product's build definitions 
        for building packages for those build definitions.
        @return: rMake configuration object suitable for use with the current
        product, and a dictionary of {flavor : contextName} lists that match 
        the flavors in the current product's build definitions.
        """

        if self._rmakeConfigWithContexts:
            return self._rmakeConfigWithContexts
        cfg = self._getRmakeConfig(useCache=False)
        conaryFacade = self._handle.facade.conary
        buildFlavors = [x[1] 
                        for x in self._handle.productStore.getGroupFlavors() ]
        contextNames = conaryFacade._getShortFlavorDescriptors(buildFlavors)
        for flavor, name in contextNames.items():
            cfg.configLine('[%s]' % name)
            cfg.configLine('flavor %s' % flavor)
            cfg.configLine('buildFlavor %s' % str(flavor))
        # TODO: add cfg interface for resetting the section to default
        cfg._sectionName = None
        self._rmakeConfigWithContexts = (cfg, contextNames)
        return cfg, contextNames

    def _getRmakeHelperWithContexts(self):
        """
        @return: an rMakeHelper object suitable for use with the current
        product, and a dictionary of {flavor : contextName} lists that match the
        flavors in the current product's build definitions.
        """
        cfg, contextDict = self._getRmakeConfigWithContexts()
        client = helper.rMakeHelper(buildConfig=cfg, plugins=self._plugins)
        return client, contextDict

    def _getRmakeContexts(self):
        _, contextDict = self._getRmakeConfigWithContexts()
        return contextDict

    def _getRmakeHelper(self):
        """
        @return: an rMakeHelper object suitable for use with the current
        product (without any contexts for use in starting a build)
        """
        cfg = self._getRmakeConfig()
        return helper.rMakeHelper(buildConfig=cfg)

    def createBuildJobForStage(self, itemList, recurse=True):
        """
        @param itemList: list of troveSpec style items to build or paths to 
        recipes.  May include version (after =) flavor (in []) or context
        (in {}) for each item.
        @type itemList: list of strings
        @param recurse: if True, build all child packages included in groups.
        @return: an rMakeHelper object suitable for use with the current
        product (without any contexts for use in starting a build)
        """
        rmakeClient = self._getRmakeHelperWithContexts()[0]
        stageLabel = self._handle.productStore.getActiveStageLabel()
        if recurse:
            recurse = rmakeClient.BUILD_RECURSE_GROUPS_SOURCE
        return rmakeClient.createBuildJob(itemList,
                                   rebuild=True,
                                   recurseGroups=recurse,
                                   limitToLabels=[stageLabel])

    def createImagesJobForStage(self):
        rmakeClient = self._getRmakeHelper()
        conaryFacade = self._handle.facade.conary
        stageName = self._handle.productStore.getActiveStageName()
        stageLabel = self._handle.productStore.getActiveStageLabel()
        product = self._handle.product
        productName = str(product.getProductShortname())
        versionName = str(product.getProductVersion())
        builds = self._handle.productStore.getBuildsWithFullFlavors(stageName)
        allImages = []
        for build, buildFlavor in builds:
            buildFlavor = conaryFacade._getFlavor(buildFlavor)
            groupName = str(build.getBuildImageGroup())
            buildImageName = str(build.getBuildName())
            buildImageType = build.getBuildImageType().tag
            buildSettings = build.getBuildImageType().fields.copy()
            troveSpec = (groupName, stageLabel, buildFlavor)
            allImages.append((troveSpec, buildImageType, buildSettings, buildImageName))

        return rmakeClient.createImageJob(productName, allImages)

    def buildJob(self, job):
        """
        Submits the given job to the rMake server
        @param job: rMake job to submit
        @return: jobId of the job that is started
        """
        client = self._getRmakeHelper()
        return client.buildJob(job)

    def watchAndCommitJob(self, jobId):
        """
        Waits for the job to commit and watches.
        @param jobId: id of the job to watch and commit.
        """
        client = self._getRmakeHelper()
        client.watch(jobId, commit=True, showTroveLogs=True,
                showBuildLogs=True, message='Automatic commit by rbuild')

    def watchJob(self, jobId):
        """
        Output progress of the job to stdout.
        @param jobId: id of the job to watch
        """
        client = self._getRmakeHelper()
        client.watch(jobId, showTroveLogs=True, showBuildLogs=True)

    def displayJob(self, jobId, troveList=None, showLogs=False):
        client = self._getRmakeHelper()
        query.displayJobInfo(client, jobId, troveList, showLogs=showLogs,
                             displayTroves=True)

    @staticmethod
    def overlayJob(job1, job2):
        if job1 is None:
            job1 = job2
        else:
            for buildTrove in job2.iterTroves():
                job1.addBuildTrove(buildTrove)
            job1Configs = job1.getConfigDict()
            job2Configs = job2.getConfigDict()
            for context, config in job1Configs.iteritems():
                if context in job2Configs:
                    config.buildTroveSpecs.extend(
                                    job2Configs[context].buildTroveSpecs)
            prebuiltBinaries = set(job1.getMainConfig().prebuiltBinaries
                                    +   job2.getMainConfig().prebuiltBinaries)
            job1.getMainConfig().prebuiltBinaries = list(prebuiltBinaries)
        job1.getMainConfig().primaryTroves = list(job2.iterTroveList(True))
        return job1
