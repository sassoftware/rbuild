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
import sys
import tempfile

from testutils import mock
from rbuild_test import rbuildhelp
from rbuild_test import resources
from rmake_test import resources as rmake_resources

from rbuild import errors
from rbuild import rbuildcfg

class ConfigTest(rbuildhelp.RbuildHelper):

    def assertEqualsText(self, a, b):
        if a == b:
            return
        print >> sys.stderr
        print >> sys.stderr, "Mismatch between text blobs:"
        af = tempfile.NamedTemporaryFile(prefix='one.')
        af.write(a)
        af.flush()
        bf = tempfile.NamedTemporaryFile(prefix='two.')
        bf.write(b)
        bf.flush()
        sys.stdout.flush()
        sys.stderr.flush()
        os.system("diff -u %s %s >&2" % (af.name, bf.name))
        raise AssertionError("Text does not match")

    def testDisplayConfig(self):
        handle = self.getRbuildHandle(mockOutput=False)
        _, txt = self.captureOutput(handle.Config.displayConfig)
        expectedText = '''\
contact                   http://bugzilla.rpath.com/
name                      Test
pluginDirs                %s
quiet                     False
repositoryMap             []
rmakePluginDirs           %s
serverUrl                 some non-empty value
signatureKeyMap           []
user                      test <password>
''' % (resources.get_plugin_dirs()[0], rmake_resources.get_plugin_dirs()[0])
        self.assertEqualsText(txt, expectedText)

        _, txt = self.captureOutput(handle.Config.displayConfig, 
                                    hidePasswords=False)
        expectedPasswordText = '''\
contact                   http://bugzilla.rpath.com/
name                      Test
pluginDirs                %s
quiet                     False
repositoryMap             []
rmakePluginDirs           %s
serverUrl                 some non-empty value
signatureKeyMap           []
user                      test foo
''' % (resources.get_plugin_dirs()[0], rmake_resources.get_plugin_dirs()[0])
        self.assertEqualsText(txt, expectedPasswordText)

    def testConfigCommand(self):
        handle = self.getRbuildHandle()
        handle.Config.registerCommands()
        handle.Config.initialize()

        mock.mockMethod(handle.Config.displayConfig)
        cmd = handle.Commands.getCommandClass('config')()
        cmd.runCommand(handle, {}, ['rbuild', 'config'])
        handle.Config.displayConfig._mock.assertCalled()

        mock.mockMethod(handle.Config.updateConfig)
        cmd.runCommand(handle, {'ask':True}, ['rbuild', 'config'])
        handle.Config.updateConfig._mock.assertCalled()

        mock.mockMethod(handle.Config.writeConaryConfiguration)
        cmd.runCommand(handle, {'conaryrc':True}, ['rbuild', 'config'])
        handle.Config.writeConaryConfiguration._mock.assertCalled()

        mock.mockMethod(handle.Config.writeRmakeConfiguration)
        cmd.runCommand(handle, {'rmakerc':True}, ['rbuild', 'config'])
        handle.Config.writeRmakeConfiguration._mock.assertCalled()

    def testConfigCommandArgParsing(self):
        self.getRbuildHandle() # required for test to run alone
        self.checkRbuild('config --ask',
            'rbuild_plugins.config.ConfigCommand.runCommand',
            [None, None, {'ask' : True},
            ['rbuild', 'config']])
        self.checkRbuild('config --conaryrc',
            'rbuild_plugins.config.ConfigCommand.runCommand',
            [None, None, {'conaryrc' : True},
            ['rbuild', 'config']])
        self.checkRbuild('config --rmakerc',
            'rbuild_plugins.config.ConfigCommand.runCommand',
            [None, None, {'rmakerc' : True},
            ['rbuild', 'config']])

    def testRequiresHomeFailure(self):
        handle = self.getRbuildHandle()
        # success cases are tested elsewhere
        oldHome = os.environ['HOME']
        try:
            os.environ['HOME'] = '/this/really/does/not/exist'
            self.assertRaises(errors.PluginError,
                              handle.Config.initializeConfig)
            del os.environ['HOME']
            self.assertRaises(errors.PluginError,
                              handle.Config.initializeConfig)
        finally:
            os.environ['HOME'] = oldHome

    def testInitializeConfig(self):
        homeDir = self.workDir + '/home'
        os.mkdir(homeDir)
        oldHome = os.environ['HOME']
        try:
            os.environ['HOME'] = homeDir
            handle = self.getRbuildHandle(productStore=mock.MockObject(),
                                          mockOutput=False)
            m1 = mock.mockMethod(handle.ui.input)
            m1._mock.setDefaultReturns([
                'http://localhost',
               'testuser',
               # (password func is mocked)
               'Y', # Use same URL for rmake
               'Y', # Save password in config file
               'Contact',
               'Display Name',
               ])
            m1._mock.setFailOnMismatch()
            m2 = mock.mockMethod(handle.ui.inputPassword)
            m2._mock.setDefaultReturns(['testpass','last'])
            m2._mock.setFailOnMismatch()
            mock.mockMethod(handle.facade.rbuilder.validateUrl) \
                ._mock.setReturn(True)
            mock.mockMethod(handle.facade.rbuilder.validateRbuilderUrl) \
                ._mock.setReturn(True)
            mock.mockMethod(handle.facade.rbuilder.validateCredentials) \
                ._mock.setReturn({'authorized':True})
            mock.mockMethod(handle.facade.rbuilder.checkForRmake)._mock.setReturn(True)
            mock.mockMethod(handle.facade.conary._parseRBuilderConfigFile)

            rc, txt = self.captureOutput(handle.Config.initializeConfig)

            # make sure all of our mock retruns were consumed correctly
            self.assertEquals(len(m1._mock.calls), 6)
            self.assertEquals(len(m2._mock.calls), 1)
            expectedUnconfiguredTxt = '''\
********************************************************
Welcome to rBuild!  Your configuration is incomplete.
Please answer the following questions to begin using rBuild:

rBuilder contacted successfully.
rBuilder authorized successfully.
rBuild configuration complete.  To rerun this configuration test run rbuild config --ask, or simply edit ~/.rbuildrc.

You should now begin working with a product by running 'rbuild init <short name> <version>'
'''
            #self.assertEqualsText(txt, expectedUnconfiguredTxt)
            txt = open(self.workDir + '/home/.rbuildrc').read()
            expectedConfiguredTxt = '''\
# This file will be overwritten by the "rbuild config --ask" command
# contact (Default: None)
contact                   Display Name
# name (Default: None)
name                      Contact
# pluginDirs (Default: /usr/share/rbuild/plugins:~/.rbuild/plugins.d)
pluginDirs                %s
# quiet (Default: False)
quiet                     False
# repositoryMap (Default: [])
repositoryMap             []
# rmakePluginDirs (Default: /usr/share/rmake/plugins:~/.rmake/plugins.d)
rmakePluginDirs           %s
# rmakeUrl (Default: None)
rmakeUrl                  https://localhost:9999
# rmakeUser (Default: None)
# serverUrl (Default: None)
serverUrl                 http://localhost
# signatureKey (Default: None)
# signatureKeyMap (Default: [])
signatureKeyMap           []
# user (Default: None)
user                      testuser testpass
''' % (resources.get_plugin_dirs()[0], rmake_resources.get_plugin_dirs()[0])
            self.assertEqualsText(txt, expectedConfiguredTxt)
            #Test to see that the permissions are set correctly
            self.assertEquals(os.stat(self.workDir + '/home/.rbuildrc').st_mode & 0777, 0600)

            # Now test contents of synced conary/rmake config files
            expectedTxt = '''\
# Include config file maintained by rBuild:
includeConfigFile ~/.conaryrc-rbuild
'''
            txt = open(self.workDir + '/home/.conaryrc').read()
            self.assertEqualsText(txt, expectedTxt)
            self.assertEquals(os.stat(self.workDir + '/home/.conaryrc').st_mode & 0777, 0600)

            expectedTxt = '''\
# Include config file maintained by rBuild:
includeConfigFile ~/.rmakerc-rbuild
'''
            txt = open(self.workDir + '/home/.rmakerc').read()
            self.assertEqualsText(txt, expectedTxt)
            self.assertEquals(os.stat(self.workDir + '/home/.rmakerc').st_mode & 0777, 0600)

            expectedTxt = '''\
# This file will be overwritten automatically by rBuild
# You can ignore it by removing the associated includeConfigFile
# line from ~/.conaryrc
# contact (Default: None)
contact                   Display Name
# name (Default: None)
name                      Contact
# repositoryMap (Default: [])
repositoryMap             []
# user (Default: [])
user                      * testuser testpass
'''
            txt = open(self.workDir + '/home/.conaryrc-rbuild').read()
            self.assertEqualsText(txt, expectedTxt)
            self.assertEquals(os.stat(self.workDir + '/home/.conaryrc-rbuild').st_mode & 0777, 0600)

            expectedTxt = '''\
# This file will be overwritten automatically by rBuild.
# You can ignore it by removing the associated includeConfigFile
# line from ~/.rmakerc
# rbuilderUrl (Default: https://localhost/)
rbuilderUrl               http://localhost
# rmakeUrl (Default: unix:///var/lib/rmake/socket)
rmakeUrl                  https://localhost:9999
# rmakeUser (Default: None)
rmakeUser                 testuser testpass
'''
            txt = open(self.workDir + '/home/.rmakerc-rbuild').read()
            self.assertEqualsText(txt, expectedTxt)
            self.assertEquals(os.stat(self.workDir + '/home/.rmakerc-rbuild').st_mode & 0777, 0600)


        finally:
            os.environ['HOME'] = oldHome


    def testInitializeConfigFromExistingData(self):
        homeDir = self.workDir + '/home'
        os.mkdir(homeDir)
        oldHome = os.environ['HOME']
        self.rbuildCfg.user = None
        self.rbuildCfg.contact = None
        self.rbuildCfg.name = None
        self.rbuildCfg.serverUrl = None
        try:
            os.environ['HOME'] = homeDir
            handle = self.getRbuildHandle(productStore=mock.MockObject(),
                                          mockOutput=False)
            m = mock.mockMethod(handle.ui.input)
            m._mock.setDefaultReturns(['', '', '', ''])
            m = mock.mockMethod(handle.ui.inputPassword)
            m._mock.setDefaultReturns([''])
            mock.mockMethod(handle.facade.rbuilder.validateUrl)._mock.setReturn(True)
            mock.mockMethod(handle.facade.rbuilder.validateRbuilderUrl)._mock.setReturn(True)
            mock.mockMethod(handle.facade.rbuilder.validateCredentials)._mock.setReturn(
                {'authorized':True})
            mock.mockMethod(handle.facade.conary._parseRBuilderConfigFile)

            # provide existing data
            mock.mockMethod(handle.facade.rbuilder._getBaseServerUrlData)._mock.setReturn(('http://localhost', 'testuser', 'testpass'))
            mockccfg = mock.MockObject()
            mockccfg._mock.enable('name')
            mockccfg.name = 'Display Name'
            mockccfg._mock.enable('contact')
            mockccfg.contact = 'Contact'
            mock.mockMethod(handle.facade.conary._getBaseConaryConfig)._mock.setReturn(mockccfg)
            mockrcfg = mock.MockObject()
            mockrcfg._mock.enable('rmakeUrl')
            mockrcfg.rmakeUrl = 'https://localhost:9999'
            mockrcfg._mock.enable('rmakeUser')
            mockrcfg.rmakeUser = ('user1', 'password1')
            mock.mockMethod(handle.facade.rmake._getBaseRmakeConfig)._mock.setReturn(mockrcfg)

            rc, txt = self.captureOutput(handle.Config.initializeConfig)
            expectedUnconfiguredTxt = '''\
********************************************************
Welcome to rBuild!  Your configuration is incomplete.
Please answer the following questions to begin using rBuild:

rBuilder contacted successfully.
rBuilder authorized successfully.
rBuild configuration complete.  To rerun this configuration test run rbuild config --ask, or simply edit ~/.rbuildrc.

You should now begin working with a product by running 'rbuild init <short name> <version>'
'''
            self.assertEqualsText(txt, expectedUnconfiguredTxt)
            txt = open(self.workDir + '/home/.rbuildrc').read()
            expectedConfiguredTxt = '''\
# This file will be overwritten by the "rbuild config --ask" command
# contact (Default: None)
contact                   Contact
# name (Default: None)
name                      Display Name
# pluginDirs (Default: /usr/share/rbuild/plugins:~/.rbuild/plugins.d)
pluginDirs                %s
# quiet (Default: False)
quiet                     False
# repositoryMap (Default: [])
repositoryMap             []
# rmakePluginDirs (Default: /usr/share/rmake/plugins:~/.rmake/plugins.d)
rmakePluginDirs           %s
# rmakeUrl (Default: None)
rmakeUrl                  https://localhost:9999
# rmakeUser (Default: None)
# serverUrl (Default: None)
serverUrl                 http://localhost
# signatureKey (Default: None)
# signatureKeyMap (Default: [])
signatureKeyMap           []
# user (Default: None)
user                      testuser
''' % (resources.get_plugin_dirs()[0], rmake_resources.get_plugin_dirs()[0])
            self.assertEqualsText(txt, expectedConfiguredTxt)
            #Test to see that the permissions are set correctly
            self.assertEquals(os.stat(self.workDir + '/home/.rbuildrc').st_mode & 0777, 0600)
        finally:
            os.environ['HOME'] = oldHome

    def testIsComplete(self):
        handle = self.getRbuildHandle()
        cfg = rbuildcfg.RbuildConfiguration()
        assert(not handle.Config.isComplete(cfg))
        cfg.serverUrl = 'foo'
        assert(not handle.Config.isComplete(cfg))
        cfg.user = ('foo', 'bar')
        assert(not handle.Config.isComplete(cfg))
        cfg.name = 'Name'
        assert(not handle.Config.isComplete(cfg))
        cfg.contact = 'Contact'
        assert(handle.Config.isComplete(cfg))

    def testUpdateConfig(self):
        homeDir = self.workDir + '/home'
        os.mkdir(homeDir)
        oldHome = os.environ['HOME']
        try:
            os.environ['HOME'] = homeDir
            handle = self.getRbuildHandle(productStore=mock.MockObject(),
                                          mockOutput=False)
            cfg = handle._cfg
            cfg.user = None
            cfg.rmakeUrl = 'https://localhost:9999'
            m = mock.mockMethod(handle.ui.input)

            m._mock.setDefaultReturns(['http://localhost/',
                                       'testuser', 'N', 'N', 'Contact',
                                       'Display Name'])
            m = mock.mockMethod(handle.ui.inputPassword)
            m._mock.setDefaultReturns(['testpass'])
            mock.mockMethod(handle.facade.rbuilder.validateUrl)._mock.setReturn(True)
            mock.mockMethod(handle.facade.rbuilder.checkForRmake)._mock.setReturn(True)
            mock.mockMethod(handle.facade.rbuilder.validateRbuilderUrl)._mock.setReturn(True)
            mock.mockMethod(handle.facade.rbuilder.validateCredentials)._mock.setReturn(
                {'authorized':True})
            mock.mockMethod(handle.facade.conary._parseRBuilderConfigFile)
            rc, txt = self.captureOutput(handle.Config.updateConfig)
            self.assertEquals(txt, 'rBuilder contacted successfully.\nrBuilder authorized successfully.\n')
            txt = open(self.workDir + '/home/.rbuildrc').read()
            expectedText = '''\
# This file will be overwritten by the "rbuild config --ask" command
# contact (Default: None)
contact                   Display Name
# name (Default: None)
name                      Contact
# pluginDirs (Default: /usr/share/rbuild/plugins:~/.rbuild/plugins.d)
pluginDirs                %s
# quiet (Default: False)
quiet                     False
# repositoryMap (Default: [])
repositoryMap             []
# rmakePluginDirs (Default: /usr/share/rmake/plugins:~/.rmake/plugins.d)
rmakePluginDirs           %s
# rmakeUrl (Default: None)
rmakeUrl                  https://localhost:9999
# rmakeUser (Default: None)
# serverUrl (Default: None)
serverUrl                 http://localhost
# signatureKey (Default: None)
# signatureKeyMap (Default: [])
signatureKeyMap           []
# user (Default: None)
user                      testuser
''' % (resources.get_plugin_dirs()[0], rmake_resources.get_plugin_dirs()[0])
            self.assertEqualsText(txt, expectedText)

        finally:
            os.environ['HOME'] = oldHome

    def testUpdateConfigRmakeUrl(self):
        homeDir = self.workDir + '/home'
        os.mkdir(homeDir)
        oldHome = os.environ['HOME']
        try:
            os.environ['HOME'] = homeDir
            handle = self.getRbuildHandle(productStore=mock.MockObject(),
                                          mockOutput=False)
            cfg = handle._cfg
            cfg.user = None
            m = mock.mockMethod(handle.ui.input)
            m._mock.setDefaultReturns(['http://localhost/',
                                       'testuser', 'Y', 'N', 'Contact',
                                       'Display Name'])
            m = mock.mockMethod(handle.ui.inputPassword)
            m._mock.setDefaultReturns(['testpass'])
            mock.mockMethod(handle.facade.rbuilder.validateUrl)._mock.setReturn(True)
            mock.mockMethod(handle.facade.rbuilder.checkForRmake)._mock.setDefaultReturn(True)
            mock.mockMethod(handle.facade.rbuilder.validateRbuilderUrl)._mock.setReturn(True)
            mock.mockMethod(handle.facade.rbuilder.validateCredentials)._mock.setReturn(
                {'authorized':True})
            mock.mockMethod(handle.facade.conary._parseRBuilderConfigFile)
            rc, txt = self.captureOutput(handle.Config.updateConfig)
            self.assertEquals(txt, 'rBuilder contacted successfully.\nrBuilder authorized successfully.\n')
            txt = open(self.workDir + '/home/.rbuildrc').read()
            expectedText = '''\
# This file will be overwritten by the "rbuild config --ask" command
# contact (Default: None)
contact                   Display Name
# name (Default: None)
name                      Contact
# pluginDirs (Default: /usr/share/rbuild/plugins:~/.rbuild/plugins.d)
pluginDirs                %s
# quiet (Default: False)
quiet                     False
# repositoryMap (Default: [])
repositoryMap             []
# rmakePluginDirs (Default: /usr/share/rmake/plugins:~/.rmake/plugins.d)
rmakePluginDirs           %s
# rmakeUrl (Default: None)
rmakeUrl                  https://localhost:9999
# rmakeUser (Default: None)
# serverUrl (Default: None)
serverUrl                 http://localhost
# signatureKey (Default: None)
# signatureKeyMap (Default: [])
signatureKeyMap           []
# user (Default: None)
user                      testuser
''' % (resources.get_plugin_dirs()[0], rmake_resources.get_plugin_dirs()[0])

            self.assertEqualsText(txt, expectedText)

        finally:
            os.environ['HOME'] = oldHome

    def testUpdateConfigBadUrl(self):
        homeDir = self.workDir + '/home'
        os.mkdir(homeDir)
        oldHome = os.environ['HOME']
        try:
            os.environ['HOME'] = homeDir
            handle = self.getRbuildHandle(productStore=mock.MockObject(),
                                          mockOutput=False)
            cfg = handle._cfg
            cfg.user = None
            m = mock.mockMethod(handle.ui.input)

            m._mock.setDefaultReturns(['http://localhost',
                                       'testuser', 'Contact',
                                       'Display Name'])
            m = mock.mockMethod(handle.ui.inputPassword)
            m._mock.setDefaultReturns(['testpass'])
            mock.mockMethod(handle.facade.rbuilder.validateUrl)._mock.setReturn(True)
            mock.mockMethod(handle.facade.rbuilder.validateRbuilderUrl)._mock.setReturn(
                (False, 'bad url'), 'http://localhost')
            mock.mockMethod(handle.facade.rbuilder.validateCredentials)._mock.setReturn(
                True, 'testuser', 'testpass', 'http://localhost')
            mock.mockMethod(handle.facade.conary._parseRBuilderConfigFile)

            rc, txt = self.captureOutput(handle.Config.updateConfig)
            expectedTxt = '''\
rBuilder contacted successfully.
The rBuilder url is a valid server, but there was an error communicating with the rBuilder at that location: bad url
rBuilder authorized successfully.
'''
            self.assertEqualsText(txt, expectedTxt)
           
            handle.ui.input._mock.clearReturn()
            handle.ui.input._mock.setDefaultReturns(['http://localhost',
                                       'N', 'testuser', 'Contact',
                                       'Display Name'])
            handle.facade.rbuilder.validateCredentials._mock.setReturn(
                False, 'testuser', 'testpass', 'http://localhost')
            rc, txt = self.captureOutput(handle.Config.updateConfig)
            expectedTxt = '''\
rBuilder contacted successfully.
The rBuilder url is a valid server, but there was an error communicating with the rBuilder at that location: bad url
The specified credentials were not successfully authorized against the rBuilder at http://localhost.
'''
            self.assertEqualsText(txt, expectedTxt)

            handle.ui.input._mock.clearReturn()
            handle.ui.input._mock.setDefaultReturns(['http://localhost',
                                       'N', 'testuser', 'Y', 'http://localhost', 'Contact',
                                       'Display Name'])
            handle.facade.rbuilder.validateCredentials._mock.setReturn(
                False, 'testuser', 'testpass', 'http://localhost')
            rc, txt = self.captureOutput(handle.Config.updateConfig)
            expectedTxt = '''\
rBuilder contacted successfully.
The rBuilder url is a valid server, but there was an error communicating with the rBuilder at that location: bad url
The specified credentials were not successfully authorized against the rBuilder at http://localhost.
rBuilder contacted successfully.
The rBuilder url is a valid server, but there was an error communicating with the rBuilder at that location: bad url
The specified credentials were not successfully authorized against the rBuilder at http://localhost.
'''            
            self.assertEqualsText(txt, expectedTxt)

            handle.ui.input._mock.clearReturn()
            handle.ui.input._mock.setDefaultReturns(['http://localhost',
                                       'Y', 'testuser', 'Y', 'http://localhost', 'Contact',
                                       'Display Name'])
            handle.facade.rbuilder.validateUrl._mock.setReturn(False)
            handle.facade.rbuilder.validateCredentials._mock.setReturn(
                False, 'testuser', 'testpass', 'http://localhost')
            rc, txt = self.captureOutput(handle.Config.updateConfig)
            expectedTxt = '''\
rBuilder contacted successfully.
The rBuilder url is a valid server, but there was an error communicating with the rBuilder at that location: bad url
rBuilder contacted successfully.
rBuilder authorized successfully.
'''
            self.assertEqualsText(txt, expectedTxt)


        finally:
            os.environ['HOME'] = oldHome


    def testWriteConfiguration(self):
        '''
        This tests the cases that aren't handled within other
        tests that cover the main functionality of _writeConfiguration
        '''
        # _functions are not accessible through handle
        from rbuild_plugins import config
        cfg = mock.MockObject()

        # once to write
        config.Config._writeConfiguration(self.workDir + '/test', cfg=cfg,
            header=None, keys=None, replaceExisting=False)
        assert cfg.store._mock.popCall(), 'Failed to store config'
        s = os.stat(self.workDir + '/test')
        self.assertEquals(s.st_mode & 0777, 0600)
        self.assertEquals(s.st_size, 0)

        # again to not write
        file(self.workDir + '/test', 'w').write('asdf')
        config.Config._writeConfiguration(self.workDir + '/test', cfg=cfg,
            header=None, keys=None, replaceExisting=False)
        cfg.store._mock.assertNotCalled()
        t = os.stat(self.workDir + '/test')
        self.assertEquals(t.st_size, 4)

    def testInitializeConfigNoPassword(self):
        homeDir = self.workDir + '/home'
        os.mkdir(homeDir)
        oldHome = os.environ['HOME']
        try:
            os.environ['HOME'] = homeDir
            handle = self.getRbuildHandle(productStore=mock.MockObject(),
                                          mockOutput=False)
            m1 = mock.mockMethod(handle.ui.input)
            m1._mock.setDefaultReturns([
                'http://localhost',
               'testuser',
               # (password func is mocked)
               'Y', # Use same URL for rmake
               'N', # Save password in config file
               'Contact',
               'Display Name',
               ])
            m1._mock.setFailOnMismatch()
            m2 = mock.mockMethod(handle.ui.inputPassword)
            m2._mock.setDefaultReturns(['testpass','last'])
            m2._mock.setFailOnMismatch()
            mock.mockMethod(handle.facade.rbuilder.validateUrl) \
                ._mock.setReturn(True)
            mock.mockMethod(handle.facade.rbuilder.validateRbuilderUrl) \
                ._mock.setReturn(True)
            mock.mockMethod(handle.facade.rbuilder.validateCredentials) \
                ._mock.setReturn({'authorized':True})
            mock.mockMethod(handle.facade.rbuilder.checkForRmake)._mock.setReturn(True)
            mock.mockMethod(handle.facade.conary._parseRBuilderConfigFile)

            rc, txt = self.captureOutput(handle.Config.initializeConfig)

            # make sure all of our mock retruns were consumed correctly
            self.assertEquals(len(m1._mock.calls), 6)
            self.assertEquals(len(m2._mock.calls), 1)
            expectedUnconfiguredTxt = '''\
********************************************************
Welcome to rBuild!  Your configuration is incomplete.
Please answer the following questions to begin using rBuild:

rBuilder contacted successfully.
rBuilder authorized successfully.
rBuild configuration complete.  To rerun this configuration test run rbuild config --ask, or simply edit ~/.rbuildrc.

You should now begin working with a product by running 'rbuild init <short name> <version>'
'''
            self.assertEqualsText(txt, expectedUnconfiguredTxt)
            txt = open(self.workDir + '/home/.rbuildrc').read()
            expectedConfiguredTxt = '''\
# This file will be overwritten by the "rbuild config --ask" command
# contact (Default: None)
contact                   Display Name
# name (Default: None)
name                      Contact
# pluginDirs (Default: /usr/share/rbuild/plugins:~/.rbuild/plugins.d)
pluginDirs                %s
# quiet (Default: False)
quiet                     False
# repositoryMap (Default: [])
repositoryMap             []
# rmakePluginDirs (Default: /usr/share/rmake/plugins:~/.rmake/plugins.d)
rmakePluginDirs           %s
# rmakeUrl (Default: None)
rmakeUrl                  https://localhost:9999
# rmakeUser (Default: None)
# serverUrl (Default: None)
serverUrl                 http://localhost
# signatureKey (Default: None)
# signatureKeyMap (Default: [])
signatureKeyMap           []
# user (Default: None)
user                      testuser
''' % (resources.get_plugin_dirs()[0], rmake_resources.get_plugin_dirs()[0])
            self.assertEqualsText(txt, expectedConfiguredTxt)
            #Test to see that the permissions are set correctly
            self.assertEquals(os.stat(self.workDir + '/home/.rbuildrc').st_mode & 0777, 0600)

            # Now test contents of synced conary/rmake config files
            expectedTxt = '''\
# Include config file maintained by rBuild:
includeConfigFile ~/.conaryrc-rbuild
'''
            txt = open(self.workDir + '/home/.conaryrc').read()
            self.assertEqualsText(txt, expectedTxt)
            self.assertEquals(os.stat(self.workDir + '/home/.conaryrc').st_mode & 0777, 0600)

            expectedTxt = '''\
# Include config file maintained by rBuild:
includeConfigFile ~/.rmakerc-rbuild
'''
            txt = open(self.workDir + '/home/.rmakerc').read()
            self.assertEqualsText(txt, expectedTxt)
            self.assertEquals(os.stat(self.workDir + '/home/.rmakerc').st_mode & 0777, 0600)

            expectedTxt = '''\
# This file will be overwritten automatically by rBuild
# You can ignore it by removing the associated includeConfigFile
# line from ~/.conaryrc
# contact (Default: None)
contact                   Display Name
# name (Default: None)
name                      Contact
# repositoryMap (Default: [])
repositoryMap             []
# user (Default: [])
user                      * testuser 
'''
            txt = open(self.workDir + '/home/.conaryrc-rbuild').read()
            self.assertEqualsText(txt, expectedTxt)
            self.assertEquals(os.stat(self.workDir + '/home/.conaryrc-rbuild').st_mode & 0777, 0600)

            expectedTxt = '''\
# This file will be overwritten automatically by rBuild.
# You can ignore it by removing the associated includeConfigFile
# line from ~/.rmakerc
# rbuilderUrl (Default: https://localhost/)
rbuilderUrl               http://localhost
# rmakeUrl (Default: unix:///var/lib/rmake/socket)
rmakeUrl                  https://localhost:9999
# rmakeUser (Default: None)
rmakeUser                 testuser 
'''
            txt = open(self.workDir + '/home/.rmakerc-rbuild').read()
            self.assertEqualsText(txt, expectedTxt)
            self.assertEquals(os.stat(self.workDir + '/home/.rmakerc-rbuild').st_mode & 0777, 0600)
        finally:
            os.environ['HOME'] = oldHome
