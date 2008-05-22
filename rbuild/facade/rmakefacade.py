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

    def _getRmakeConfig(self, useCache=True):
        """
        Returns an rmake configuration file that matches the product associated
        with the current handle.
        @param useCache: if True, uses a cached version of the rmake configuration
        file if available.
        @return: rMake configuration file suitable for use with the current product.
        """
        if self._rmakeConfig and useCache:
            return self._rmakeConfig
        conaryFacade = self._handle.facade.conary
        productStore = self._handle.getProductStore()
        product = productStore.get()
        stageName = productStore.getCurrentStageName()
        stageLabel = conaryFacade._getLabel(product.getLabelForStage(stageName))
        baseFlavor = conaryFacade._getFlavor(product.getBaseFlavor())
        rmakeConfigPath = productStore.getRmakeConfigPath()


        cfg = buildcfg.BuildConfiguration(False)
        cfg.resolveTrovesOnly = True
        cfg.shortenGroupFlavors = True
        cfg.ignoreExternalRebuildDeps = True

        cfg.buildLabel = stageLabel
        cfg.installLabelPath = [ stageLabel ]
        cfg.flavor = [baseFlavor]
        cfg.buildFlavor = baseFlavor
        cfg.resolveTroves = product.getUpstreamSources()

        rbuildConfig = self._handle.getConfig()
        cfg.repositoryMap = rbuildConfig.repositoryMap
        #E1101: Instance of 'BuildConfiguration' has no 'user' member - untrue
        #pylint: disable-msg=E1101
        cfg.user.append((stageLabel.getHost(),) + rbuildConfig.user)
        cfg.rmakeUrl = rbuildConfig.rmakeUrl
        cfg.rmakeUser = rbuildConfig.user

        if os.path.exists(rmakeConfigPath):
            cfg.includeConfigFile(rmakeConfigPath)

        if useCache:
            self._rmakeConfig = cfg
        return cfg

    def _getRmakeConfigWithContexts(self):
        """
        Returns an rmake configuration file that matches the product associated
        with the current handle.  Beyond the settings provided in _getRmakeConfig,
        this rmake configuration will have contexts set up that match the flavors
        required by the product's build definitions for building packages for
        those build definitions.
        @return: rMake configuration object suitable for use with the current
        product, and a dictionary of {flavor : contextName} lists that match the 
        flavors in the current product's build definitions.
        """

        if self._rmakeConfigWithContexts:
            return self._rmakeConfigWithContexts
        cfg = self._getRmakeConfig(useCache=False)
        product = self._handle.getProductStore().get()
        conaryFacade = self._handle.facade.conary
        buildFlavors = [ x.getBaseFlavor()
                         for x in product.getBuildDefinitions() ]
        buildFlavors = conaryFacade._overrideFlavors(product.getBaseFlavor(),
                                                     buildFlavors)
        contextNames = conaryFacade._getShortFlavorDescriptors(buildFlavors)
        for flavor, name in contextNames.items():
            cfg.configLine('[%s]' % name)
            cfg.configLine('flavor %s' % flavor)
            cfg.configLine('buildFlavor %s' % str(flavor))
        self._rmakeConfigWithContexts = (cfg, contextNames)
        return cfg, contextNames

    def _getRmakeHelperWithContexts(self):
        """
        @return: an rMakeHelper object suitable for use with the current
        product, and a dictionary of {flavor : contextName} lists that match the
        flavors in the current product's build definitions.
        """
        cfg, contextDict = self._getRmakeConfigWithContexts()
        client = helper.rMakeHelper(buildConfig=cfg)
        return client, contextDict

    def _getRmakeHelper(self):
        """
        @return: an rMakeHelper object suitable for use with the current
        product (without any contexts for use in starting a build)
        """
        cfg = self._getRmakeConfig()
        return helper.rMakeHelper(buildConfig=cfg)

    def createBuildJobForStage(self, itemList, recurse=True):
        """
        @return: an rMakeHelper object suitable for use with the current
        product (without any contexts for use in starting a build)
        """
        rmakeClient = self._getRmakeHelperWithContexts()[0]
        productStore = self._handle.getProductStore()
        stageName = productStore.getActiveStageName()
        product = productStore.get()
        stage = product.getStage(stageName)
        if recurse:
            recurse = rmakeClient.BUILD_RECURSE_GROUPS_SOURCE
        return rmakeClient.createBuildJob(itemList,
                                   rebuild=True,
                                   recurseGroups=recurse,
                                   limitToLabels=[stage.getLabel()])

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
