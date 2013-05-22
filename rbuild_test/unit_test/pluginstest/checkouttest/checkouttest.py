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



import os

from rbuild_test import rbuildhelp
from testutils import mock

from rbuild import errors

class CheckoutTest(rbuildhelp.RbuildHelper):
    def _getHandle(self):
        productStore = mock.MockObject(stableReturnValues=True)
        productStore.getRbuildConfigPath._mock.setReturn(
                                                self.workDir + '/rbuildrc')
        handle = self.getRbuildHandle(productStore=productStore)
        handle.Checkout.registerCommands()
        handle.Checkout.initialize()
        return handle

    def testUpdateCommandParsing(self):
        handle = self._getHandle()
        cmd = handle.Commands.getCommandClass('checkout')()
        handle.productStore.update._mock.setDefaultReturn(None)
        mock.mockMethod(handle.Checkout.checkoutPackageDefault)
        mock.mockMethod(handle.Checkout.checkoutPackage)
        mock.mockMethod(handle.Checkout.derivePackage)
        mock.mockMethod(handle.Checkout.shadowPackage)
        mock.mockMethod(handle.Checkout.newPackage)

        cmd.runCommand(handle, {}, ['rbuild', 'checkout', 'foo'])
        handle.Checkout.checkoutPackageDefault._mock.assertCalled('foo',
                                                                  template=None,
                                                                  factory=None)

        cmd.runCommand(handle, {'template': 'default'},
                       ['rbuild', 'checkout', 'foo'])
        handle.Checkout.checkoutPackageDefault._mock.assertCalled('foo',
                                                             template='default',
                                                             factory=None)

        cmd.runCommand(handle, {'template': 'default', 'factory': 'test'},
                       ['rbuild', 'checkout', 'foo'])
        handle.Checkout.checkoutPackageDefault._mock.assertCalled('foo',
                                                             template='default',
                                                             factory='test')

        cmd.runCommand(handle, dict(derive=True), ['rbuild', 'checkout', 'foo'])
        handle.Checkout.derivePackage._mock.assertCalled('foo')

        cmd.runCommand(handle, dict(new=True), ['rbuild', 'checkout', 'foo'])
        handle.Checkout.newPackage._mock.assertCalled('foo', template=None,
                                                      factory=None)

        cmd.runCommand(handle, dict(new=True, template='default'),
                       ['rbuild', 'checkout', 'foo'])
        handle.Checkout.newPackage._mock.assertCalled('foo', template='default',
                                                      factory=None)

        cmd.runCommand(handle, dict(shadow=True), ['rbuild', 'checkout', 'foo'])
        handle.Checkout.shadowPackage._mock.assertCalled('foo')

        # unknown arguments
        self.assertRaises(errors.ParseError, 
            cmd.runCommand, handle, {}, ['rbuild', 'checkout', 'foo', 'bar'])

        # two flags set
        self.assertRaises(errors.ParseError, 
            cmd.runCommand, handle, dict(shadow=True, new=True),
                        ['rbuild', 'checkout', 'foo'])

        self.assertRaises(errors.ParseError, 
            cmd.runCommand, handle, dict(shadow=True, derive=True),
                        ['rbuild', 'checkout', 'foo'])

    def testCheckoutDefaultPackage(self):
        handle = self._getHandle()
        mock.mockMethod(handle.Checkout._getUpstreamPackage)
        mock.mock(handle.Checkout, '_relPath')
        mock.mockMethod(handle.Checkout.checkoutPackage)
        mock.mockMethod(handle.Checkout.newPackage)

        # RBLD-122: avoid traceback here, make sure it's a PluginError
        # (to which we attach useful information...)
        handle.productStore = None
        self.assertRaises(errors.PluginError,
            handle.Checkout.checkoutPackageDefault, 'asdf')

        mock.mockMethod(handle.Checkout._getExistingPackage)
        handle.Checkout._getExistingPackage._mock.setDefaultReturn(
                                        self.makeTroveTuple('foo:source'))
        handle.Checkout._relPath._mock.setDefaultReturn('./foo')
        handle.Checkout.checkoutPackageDefault('foo')
        handle.Checkout._getExistingPackage._mock.assertCalled('foo')
        handle.Checkout.checkoutPackage._mock.assertCalled('foo')
        handle.Checkout.checkoutPackageDefault('foo:source')
        handle.Checkout._getExistingPackage._mock.assertCalled('foo:source')
        handle.Checkout.checkoutPackage._mock.assertCalled('foo:source')

        handle.Checkout._getExistingPackage._mock.setDefaultReturn(None)
        handle.Checkout._getUpstreamPackage._mock.setDefaultReturn(None)
        handle.Checkout.checkoutPackageDefault('foo')
        handle.Checkout._getExistingPackage._mock.assertCalled('foo')
        handle.Checkout._getUpstreamPackage._mock.assertCalled('foo')
        handle.Checkout.newPackage._mock.assertCalled('foo', template=None,
                                                             factory=None)
        handle.Checkout.checkoutPackageDefault('foo', template='default')
        handle.Checkout._getExistingPackage._mock.assertCalled('foo')
        handle.Checkout._getUpstreamPackage._mock.assertCalled('foo')
        handle.Checkout.newPackage._mock.assertCalled('foo', template='default',
                                                             factory=None)
        handle.Checkout.checkoutPackageDefault('foo', factory='thefact')
        handle.Checkout._getExistingPackage._mock.assertCalled('foo')
        handle.Checkout._getUpstreamPackage._mock.assertCalled('foo')
        handle.Checkout.newPackage._mock.assertCalled('foo', template=None,
                                                             factory='thefact')

        handle.Checkout._getUpstreamPackage._mock.setDefaultReturn(
                                                    self.makeTroveTuple('foo'))
        err = self.assertRaises(errors.PluginError,
                                handle.Checkout.checkoutPackageDefault, 'foo')
        expectedError = '\n'.join((
            'The upstream source provides a version of this package.',
            'Please specify:',
            '  --shadow to shadow this package',
            '  --derive to derive from it',
            '  --new to replace it with a new version'))
        assert str(err) == expectedError

    def testCheckoutPackage(self):
        handle = self._getHandle()
        handle.productStore.getActiveStageLabel._mock.setReturn(
                                                'conary.rpath.com@rpl:1')
        handle.productStore.getCheckoutDirectory._mock.setReturn(
                                                '/path/to/foo', 'foo')
        mock.mockMethod(handle.facade.conary.checkout)
        handle.Checkout.checkoutPackage('foo')
        handle.facade.conary.checkout._mock.assertCalled('foo',
                                                    'conary.rpath.com@rpl:1',
                                                    targetDir='/path/to/foo')

    def testDerivePackage(self):
        handle = self._getHandle()
        from rbuild_plugins.checkout import derive
        checkout = handle.Checkout
        mock.mockMethod(checkout._getUpstreamPackage)
        mock.mock(derive, 'derive')
        fooTrove = self.makeTroveTuple('foo')

        checkout._getUpstreamPackage._mock.setDefaultReturn(fooTrove)
        checkout.derivePackage('foo')
        derive.derive._mock.assertCalled(handle, fooTrove)

        checkout._getUpstreamPackage._mock.setDefaultReturn(None)
        err = self.assertRaises(errors.PluginError,
                                checkout.derivePackage, 'foo')
        self.assertEquals(str(err), 'cannot derive foo: no upstream binary')

    def testShadowPackage(self):
        handle = self._getHandle()
        checkout = handle.Checkout
        mock.mockMethod(checkout._getUpstreamPackage)
        mock.mockMethod(handle.facade.conary.shadowSourceForBinary)
        mock.mockMethod(handle.facade.conary.checkout)

        fooTrove = self.makeTroveTuple('foo')
        checkout._getUpstreamPackage._mock.setDefaultReturn(fooTrove)

        handle.productStore.getActiveStageLabel._mock.setDefaultReturn(
                                        'localhost@rpl:1')
        handle.productStore.getCheckoutDirectory._mock.setReturn(
                                                '/path/to/foo', 'foo')
        checkout.shadowPackage('foo')
        handle.facade.conary.shadowSourceForBinary._mock.assertCalled(
                                                             fooTrove[0],
                                                             fooTrove[1],
                                                             fooTrove[2],
                                                             'localhost@rpl:1')
        handle.facade.conary.checkout._mock.assertCalled('foo',
                                                     'localhost@rpl:1',
                                                     targetDir='/path/to/foo')


        checkout._getUpstreamPackage._mock.setDefaultReturn(None)
        err = self.assertRaises(errors.PluginError,
                                checkout.shadowPackage, 'foo')
        self.assertEquals(str(err), 'cannot shadow foo: no upstream binary')

    def testShadowRemotePackage(self):
        handle = self._getHandle()
        checkout = handle.Checkout
        mock.mockMethod(checkout._getRemotePackage)
        mock.mockMethod(handle.facade.conary.shadowSourceForBinary)
        mock.mockMethod(handle.facade.conary.checkout)

        fooTrove = self.makeTroveTuple('foo', 'foo.rpath.org@foo:1')
        checkout._getRemotePackage._mock.setDefaultReturn(fooTrove)

        handle.productStore.getActiveStageLabel._mock.setDefaultReturn(
                                        'localhost@rpl:1')
        handle.productStore.getCheckoutDirectory._mock.setReturn(
                                                '/path/to/foo', 'foo')
        checkout.shadowPackage('foo=foo.rpath.org@foo:1')
        handle.facade.conary.shadowSourceForBinary._mock.assertCalled(
                                                             fooTrove[0],
                                                             fooTrove[1],
                                                             fooTrove[2],
                                                             'localhost@rpl:1')
        handle.facade.conary.checkout._mock.assertCalled('foo',
                                                     'localhost@rpl:1',
                                                     targetDir='/path/to/foo')


        checkout._getRemotePackage._mock.setDefaultReturn(None)
        err = self.assertRaises(errors.PluginError,
                                checkout.shadowPackage, 'foo=foo.rpath.org@foo:1')
        self.assertEquals(str(err), '%s:source does not exist on label %s.' % \
                            ('foo', 'foo.rpath.org@foo:1'))

    def testNewPackage(self):
        handle = self._getHandle()
        checkout = handle.Checkout
        mock.mockMethod(handle.facade.conary.createNewPackage)
        handle.productStore.getActiveStageLabel._mock.setDefaultReturn(
                                        'foo.rpath.org@rpl:1')
        handle.productStore.getCheckoutDirectory._mock.setReturn(
                                                '/path/to/foo', 'foo')
        handle.productStore.getCheckoutDirectory._mock.setReturn(
                                                '/path/to/factory-foo',
                                                'factory-foo')
        mock.mockMethod(handle.Checkout._getExistingPackage)
        handle.Checkout._getExistingPackage._mock.setDefaultReturn(None)
        mock.mockMethod(handle.Checkout._getUpstreamPackage)
        handle.Checkout._getUpstreamPackage._mock.setDefaultReturn(None)
        mock.mock(handle.Checkout, '_relPath', './foo')

        checkout.newPackage('foo')
        handle.facade.conary.createNewPackage._mock.assertCalled('foo',
                                                    'foo.rpath.org@rpl:1',
                                                    targetDir='/path/to/foo',
                                                    template=None,
                                                    factory=None)
        checkout.newPackage('foo', template = 'default')
        handle.facade.conary.createNewPackage._mock.assertCalled('foo',
                                                    'foo.rpath.org@rpl:1',
                                                    targetDir='/path/to/foo',
                                                    template='default',
                                                    factory=None)
        checkout.newPackage('foo', factory = 'thefact')
        handle.facade.conary.createNewPackage._mock.assertCalled('foo',
                                                    'foo.rpath.org@rpl:1',
                                                    targetDir='/path/to/foo',
                                                    template=None,
                                                    factory='thefact')
        checkout.newPackage('factory-foo') # do NOT provide "factory ="
        handle.facade.conary.createNewPackage._mock.assertCalled('factory-foo',
                                            'foo.rpath.org@rpl:1',
                                            targetDir='/path/to/factory-foo',
                                            template=None,
                                            factory='factory')

        # change _getExistingPackage to return a package, createNewPackage
        # should not be called.
        handle.Checkout._getExistingPackage._mock.setDefaultReturn(
            self.makeTroveTuple('foo:source'))
        err = self.assertRaises(errors.PluginError,
            checkout.newPackage, 'foo')
        handle.facade.conary.createNewPackage._mock.assertNotCalled()
        self.assertEquals(str(err),
            '\n'.join(('This package already exists in the product.',
                'Use "rbuild checkout foo" to checkout the existing package '
                'to modify its files, or give the new package a different name.')))

        handle.Checkout._getExistingPackage._mock.setDefaultReturn(None)
        handle.Checkout._getUpstreamPackage._mock.setDefaultReturn(
            self.makeTroveTuple('foo:source'))
        mock.mock(handle, 'ui')
        handle.ui.getYn._mock.setDefaultReturn(True)
        checkout.newPackage('foo')
        handle.facade.conary.createNewPackage._mock.assertCalled('foo',
                                                    'foo.rpath.org@rpl:1',
                                                    targetDir='/path/to/foo',
                                                    template=None,
                                                    factory=None)

        handle.ui.getYn._mock.setDefaultReturn(False)
        checkout.newPackage('foo')
        handle.facade.conary.createNewPackage._mock.assertNotCalled()

        troveTup = self.makeTroveTuple('foobar:source', '/foo.rpath.org@foo:1//2//3')
        handle.ui.getYn._mock.setDefaultReturn(True)
        handle.Checkout._getExistingPackage._mock.setDefaultReturn(
            troveTup)
        mock.mockMethod(handle.facade.conary.detachPackage)
        checkout.newPackage('foobar')
        handle.facade.conary.detachPackage._mock.assertCalled(troveTup,
            '/' + 'foo.rpath.org@rpl:1', None)

        handle.ui.getYn._mock.setDefaultReturn(False)
        checkout.newPackage('foobar')
        handle.facade.conary.detachPackage._mock.assertNotCalled()

    def testGetUpstreamPackage(self):
        handle = self._getHandle()
        checkout = handle.Checkout
        conaryFacade = handle.facade.conary
        fooTrove = self.makeTroveTuple('foo')
        mock.mockMethod(conaryFacade._findPackageInSearchPaths)
        conaryFacade._findPackageInSearchPaths._mock.setDefaultReturn([fooTrove])
        self.assertEquals(checkout._getUpstreamPackage('foo'), fooTrove)

        conaryFacade._findPackageInSearchPaths._mock.setDefaultReturn(None)
        self.assertEquals(checkout._getUpstreamPackage('foo'), None)

    def testGetRemotePackage(self):
        handle = self._getHandle()
        checkout = handle.Checkout
        conaryFacade = handle.facade.conary
        fooTrove = self.makeTroveTuple('foo', 'foo.rpath.org@foo:1')
        mock.mockMethod(conaryFacade._findTrove)
        conaryFacade._findTrove._mock.setDefaultReturn(fooTrove)
        self.assertEquals(checkout._getRemotePackage('foo', 
                            'foo.rpath.org@foo:1'), fooTrove)
        self.assertEquals(checkout._getRemotePackage('foo:source', 
                            'foo.rpath.org@foo:1'), fooTrove)

        conaryFacade._findTrove._mock.setDefaultReturn(None)
        self.assertEquals(checkout._getRemotePackage('foo',
                            'foo.rpath.org@foo:1'), None)

    def testGetExistingPackage(self):
        handle = self._getHandle()
        checkout = handle.Checkout
        fooSource = self.makeTroveTuple('foo:source')
        handle.productStore.getActiveStageLabel._mock.setDefaultReturn(
                                                        'foo.rpath.org@rpl:1')
        mock.mockMethod(handle.facade.conary._findTrove)
        handle.facade.conary._findTrove._mock.setDefaultReturn(fooSource)

        result = checkout._getExistingPackage('foo')

        self.assertEquals(result, fooSource)
        handle.facade.conary._findTrove._mock.assertCalled('foo:source', 
                                                          'foo.rpath.org@rpl:1',
                                                          allowMissing=True)
        handle.facade.conary._findTrove._mock.setDefaultReturn(None)

    def test_relPath(self):
        handle = self._getHandle()
        checkout = handle.Checkout
        self.assertEquals(checkout._relPath('/foo/bar', '/foo/bar'),
                                            '.')
        self.assertEquals(checkout._relPath('/foo/bar', '/foo/bar/baz'),
                                            './baz')
        self.assertEquals(checkout._relPath('/foo/bar/baz', '/foo/bar'),
                                            '..')
        self.assertEquals(checkout._relPath('/foo/bar', '/foo/baz'),
                                            '../baz')
        self.assertEquals(checkout._relPath('/1/2/3/bar', '/1/2/4/baz'),
                                            '../../4/baz')
        os.chdir(self.workDir)
        self.assertEquals(checkout._relPath(self.workDir+'/bar', 'baz'),
                                            '../baz')

    def testCommand(self):
        self.getRbuildHandle()
        self.checkRbuild('checkout foo --new --shadow --derive '
                         '--template=default --factory=thefact',
                         'rbuild_plugins.checkout.CheckoutCommand.runCommand',
                         [None, None, {'derive' : True, 'new' : True,
                          'shadow' : True, 'template' : 'default',
                          'factory' : 'thefact'},
                         ['rbuild', 'checkout', 'foo']])




