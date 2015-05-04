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


import os
import shlex
import sys
import StringIO
from conary.lib import util
from proddef_test import resources as proddef_resources
from rmake_test import resources as rmake_resources
from rmake_test import rmakehelp
from rpath_proddef import api1 as proddef
from testutils import mock
import mockproddef

from rbuild import rbuildcfg
from rbuild import handle
from rbuild.internal import main
from rbuild_test import resources

#from mint_test.mint_rephelp import RepositoryHelper
from conary_test.rephelp import RepositoryHelper as RepositoryHelper


class RbuildHelper(rmakehelp.RmakeHelper):
    _newPython = sys.version_info[:2] > (2, 4)
    optparseDifferences = dict(
        options = _newPython and 'Options' or 'options',
        usage = _newPython and 'Usage' or 'usage',
    )

    def setUp(self):
        rmakehelp.RmakeHelper.setUp(self)
        self.rbuildCfg = rbuildcfg.RbuildConfiguration(readConfigFiles=False,
                root=self.cfg.root)
        self.rbuildCfg.contact = self.cfg.contact
        self.rbuildCfg.name = self.cfg.name
        self.rbuildCfg.pluginDirs = resources.get_plugin_dirs()
        self.rbuildCfg.serverUrl = 'http://example.com'
        self.rbuildCfg.rmakePluginDirs = rmake_resources.get_plugin_dirs()
        self.writeFile(self.cfg.root + '/conaryrc', '')
        self.rbuildCfg.user = ('test', 'foo')
        self.rbuildCfg.recipeTemplateDirs.insert(0,
                resources.get_test_path('config', 'recipeTemplates'))
        self.setUpSchemaDir()

    def setUpSchemaDir(self):
        schemaDir = proddef_resources.get_xsd()
        self.schemaDir = schemaDir
        self.mock(proddef.ProductDefinition, 'schemaDir', schemaDir)
        self.mock(proddef.PlatformDefinition, 'schemaDir', schemaDir)
        self.mock(proddef.Platform, 'schemaDir', schemaDir)

    def initializeFlavor(self):
        pass

    def prepopulateKeyCache(self, keyCache):
        pass

    def getRbuildHandle(self, productStore=None, cfg=None, pluginManager=None,
                        userInterface=None,
                        logRoot=None, mockOutput=True):
        # Note: order of arguments is different because code in test suite
        # assumes that first argument is productStore not cfg
        if isinstance(productStore, mock.MockObject):
            productStore.getRbuildConfigPath._mock.setReturn(
                                                    self.workDir + '/rbuildrc')
            productStore.getRmakeConfigPath._mock.setReturn(
                                                    self.workDir + '/rmakerc')
        if cfg is None:
            self.rbuildCfg.repositoryMap = self.cfg.repositoryMap
            cfg = self.rbuildCfg
        if logRoot is None:
            logRoot = self.workDir + '/.rbuild'
        h = handle.RbuildHandle(cfg=cfg,
                                pluginManager=pluginManager,
                                productStore=productStore,
                                userInterface=userInterface,
                                logRoot=logRoot)
        if mockOutput:
            h.ui.outStream = mock.MockObject()
            h.ui.errorStream = mock.MockObject()
        return h

    def enablePlugins(self):
        from rbuild.internal import pluginloader
        pluginloader.getPlugins([], self.rbuildCfg.pluginDirs)

    def addProductDefinition(self, shortName, version='1',
                             upstream=None, buildFlavors=None):
        self.cfg.initializeFlavors()
        xmlString = mockproddef.getProductDefinitionString(self.cfg,
                                                   version=version,
                                                   upstream=upstream,
                                                   buildFlavors=buildFlavors)
        location = 'localhost@rpl:%s-%s/%s-1-1' % (shortName, version, version)
        return self.addComponent('product-definition:source=%s' % location,
                                 [('product-definition.xml', xmlString),
                                  ('product-definition.recipe',
                                    productDefinitionRecipe)])

    def checkRbuild(self, cmd, fn, expectedArgs, cfgValues=None,
                    returnVal=None, ignoreKeywords=False, **expectedKw):
        if cfgValues is None:
            cfgValues = {}
        cmd = ' --skip-default-config ' + cmd
        cmd = ' --config="pluginDirs %s" ' % self.rbuildCfg.pluginDirs[0] + cmd
        configPath = '%s/etc/rbuildrc' % self.rootDir
        if not os.path.exists(configPath):
            self.rbuildCfg.writeToFile(configPath)
        cmd = ' --config-file=%s ' % configPath + cmd

        return self.checkCommand(main.main, 'rbuild ' + cmd, fn,
                                 expectedArgs, cfgValues, returnVal,
                                 ignoreKeywords, **expectedKw)

    def initProductDirectory(self, directory):
        util.mkdirChain(directory)
        util.execute('tar -xzf %s -C %s' % (
            resources.get_archive('foo-product.tgz'), directory))
        self.rbuildCfg.writeCheckoutFile(directory + '/.rbuild/rbuildrc')


class CommandTest(RbuildHelper):

    def setUp(self):
        RbuildHelper.setUp(self)
        self.getRbuildHandle()
        from rbuild_plugins import config
        mock.mock(config.Config, 'isComplete', True)
        os.chdir(self.workDir)
        self.rbuildCfg.resetToDefault('serverUrl')
        self.rbuildCfg.writeToFile(self.workDir + '/rbuildrc')

    def openRepository(self, *args, **kw):
        curDir = os.getcwd()
        try:
            os.chdir('/')
            rc = RbuildHelper.openRepository(self, *args, **kw)
            self.rbuildCfg.repositoryMap.update(self.cfg.repositoryMap)
            self.rbuildCfg.writeToFile(self.workDir + '/rbuildrc')
            return rc
        finally:
            os.chdir(curDir)

    def openRmakeRepository(self, *args, **kw):
        curDir = os.getcwd()
        try:
            os.chdir('/')
            rc = RbuildHelper.openRmakeRepository(self, *args, **kw)
            self.rbuildCfg.repositoryMap.update(self.cfg.repositoryMap)
            self.rbuildCfg.writeToFile(self.workDir + '/rbuildrc')
            return rc
        finally:
            os.chdir(curDir)

    def startRmakeServer(self, *args, **kw):
        rc = RbuildHelper.startRmakeServer(self, *args, **kw)
        self.rbuildCfg.rmakeUrl = self.rmakeCfg.rmakeUrl
        self.rbuildCfg.writeToFile(self.workDir + '/rbuildrc')
        return rc

    def runCommand(self, commandString, exitCode=0, subDir=None, stdin=''):
        curDir = None
        if subDir:
            curDir = os.getcwd()
            os.chdir(subDir)
        if len(stdin):
            stdin, sys.stdin = sys.stdin, StringIO.StringIO(stdin)
        else:
            stdin = sys.stdin
        try:
            cmd = 'rbuild --config-file=%s --skip-default-config %s'
            cmd = cmd % (self.workDir + '/rbuildrc', commandString)
            argv = shlex.split(cmd)
            try:
                rc, txt =  self.captureOutput(main.main, argv)
            except SystemExit, err:
                rc = err.code
                txt = ''
            if exitCode != rc:
                raise RuntimeError('Expected error code %s,'
                                   ' got error code %s.  Output:\n%s' %(exitCode, rc, txt))
            return txt
        finally:
            if curDir:
                os.chdir(curDir)
            sys.stdin = stdin

_reposDir = None

class RbuilderCommandTest(CommandTest, RepositoryHelper):
    def setUp(self):
        RepositoryHelper.setUp(self)
        CommandTest.setUp(self)

    def _getReposDir(self):
        global _reposDir
        from conary_test import rephelp
        _reposDir = rephelp.getReposDir(_reposDir, 'conarytest')
        return _reposDir

    def openRepository(self, *args, **kw):
        return CommandTest.openRepository(self, *args, **kw)

    def startRbuilderServer(self, *args, **kw):
        repos = self.startMintServer(*args, **kw)
        serverUrl = 'https://%s' % self.mintCfg.secureHost
        self.rbuildCfg.serverUrl = serverUrl
        self.rbuildCfg.writeToFile(self.workDir + '/rbuildrc')
        return repos

    def tearDown(self):
        RepositoryHelper.tearDown(self)
        CommandTest.tearDown(self)

productDefinitionRecipe = """
class ProductDefinition(PackageRecipe):
    name = 'product-definition'
    version = '%s'
    def setup(r):
        r.addSource('product-definition.xml')
"""
