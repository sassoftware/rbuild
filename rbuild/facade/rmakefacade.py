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

    def __init__(self, handle):
        """
        @param handle: The handle with which this instance is associated.
        """
        self._handle = handle
        self._rmakeConfig = None
        self._rmakeConfigWithContexts = None

    def _getRmakeConfig(self, withContexts=False):
        if withContexts and self._rmakeConfigWithContexts:
            return self._rmakeConfigWithContexts
        if not withContexts and self._rmakeConfig:
            return self._rmakeConfig
        conaryFacade = self._handle.conary.facade
        productStore = self._handle.getProductStore()
        product = productStore.get()
        stageName = productStore.getCurrentStageName()
        stageLabel = conaryFacade._toLabel(product.getLabelForStage(stageName))
        baseFlavor = conaryFacade._toFlavor(product.getBaseFlavor())
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

        rbuildConfig = self._handle.getRbuildConfig()
        cfg.repositoryMap = rbuildConfig.repositoryMap
        cfg.user.append((stageLabel.getHost(),) + rbuildConfig.user)
        cfg.rmakeUrl = rbuildConfig.rmakeUrl
        cfg.rmakeUser = rbuildConfig.user

        if os.path.exists(rmakeConfigPath):
            cfg.includeConfigFile(rmakeConfigPath)

        if not withContexts:
            self._rmakeConfig = cfg
            return cfg
        buildFlavors = [ x.getBaseFlavor()
                         for x in product.getBuildDefinitions() ]
        contextNames = conaryFacade._getShortFlavorDescriptors(baseFlavor,
                                                               buildFlavors)
        for flavor, name in contextNames.items():
            cfg.configLine('[%s]' % name)
            cfg.configKey('flavor %s', str(flavor))
            cfg.configKey('buildFlavor', str(flavor))
        self._rmakeConfigWithContexts = (cfg, contextNames)
        return cfg, contextNames

    def _getRmakeHelperWithContexts(self):
        cfg, contextDict = self._getRmakeConfig(withContexts=True)
        client = helper.rMakeHelper(buildConfig=cfg)
        return client, contextDict

    def _getRmakeHelper(self):
        cfg = self._getRmakeConfig()
        return helper.rMakeHelper(buildConfig=cfg)

    def createBuildJobForStage(self, itemList, stage, recurse=True):
        rmakeClient = self._getRmakeHelperWithContexts()[0]
        if recurse:
            recurse = rmakeClient.BUILD_RECURSE_GROUPS_SOURCE
        return rmakeClient.createBuildJob(itemList,
                                   rebuild=True,
                                   recurseGroups=recurse,
                                   limitToLabels=[str(stage.label)])

    def setPrimaryJob(self, job, job2):
        if job is not None:
            for buildTrove in job2.iterTroves():
                job.addBuildTrove(buildTrove)
        else:
            job = job2
        job.getMainConfig().primaryTroves = list(job2.iterTroveList(True))
        return job

    def buildJob(self, job):
        client = self._getRmakeHelper()
        return client.buildJob(job)

    def watchAndCommitJob(self, jobId):
        client = self._getRmakeHelper()
        client.watch(jobId, commit=True, showTroveLogs=True,
                showBuildLogs=True, message='Automatic commit by rbuild')
