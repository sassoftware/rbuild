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
import time

from rbuild_test import rbuildhelp
from conary_test import recipes

from conary.lib import util


class CheckoutTest(rbuildhelp.CommandTest):
    def testCheckoutNoOption(self):
        self.openRepository()
        self.initProductDirectory('foo')
        # bogus top level group with nothing relevant in it.
        self.addCollection('group-dist', ['simple:run'])
        os.chdir('foo/devel')
        txt = self.runCommand('checkout package')
        self.assertEquals(txt, "Created new package 'package' in './package'\n")
        os.chdir('package')
        assert('@NEW@' in open('CONARY').read())

    def testCheckoutShadow(self):
        self.openRepository()
        self.addComponent('simple:source', 
                         [('simple.recipe', recipes.simpleRecipe)])
        self.addComponent('simple:runtime')
        self.addCollection('simple', [':runtime'])
        trv = self.addCollection('group-dist', ['simple'])
        self.initProductDirectory('foo')
        os.chdir('foo/devel')
        txt = self.runCommand('checkout simple', exitCode=1)
        expectedText = '\n'.join((
            'error: The upstream source provides a version of this package.',
            'Please specify:',
            '  --shadow to shadow this package',
            '  --derive to derive from it',
            '  --new to replace it with a new version',
            ''))
        assert txt == expectedText
        txt = self.runCommand('checkout simple --shadow')
        self.assertEquals(txt, "Shadowed package 'simple' in './simple'\n")
        os.chdir('simple')
        assert('@NEW@' not in open('CONARY').read())
        trv = self.findAndGetTrove('simple:source=localhost@foo:foo-1-devel')
        self.assertEquals(str(trv.getVersion()),
                          '/localhost@rpl:linux//foo:foo-1-devel/1.0-1')
        os.chdir('..')
        util.rmtree('simple')
        txt = self.runCommand('checkout simple')
        self.assertEquals(txt, "Checked out existing package 'simple' in './simple'\n")
        os.chdir('simple')
        assert('@NEW@' not in open('CONARY').read())

    def testDerive(self):
        self.openRepository()
        self.addComponent('simple:source', 
                         [('simple.recipe', recipes.simpleRecipe),
                          ('extrafile', 'foo'),
                          ('subdir/foo', 'bar')])
        self.addComponent('simple:runtime', 
                          [('/some/file', 'contents\n')])
        self.addCollection('simple', [':runtime'])
        trv = self.addCollection('group-dist', ['simple'])
        self.initProductDirectory('foo')
        os.chdir('foo/devel')
        txt = self.runCommand('checkout simple --derive')
        self.assertEquals(txt, '''\
Shadowing simple=/localhost@rpl:linux/1.0-1-1[] onto localhost@foo:foo-1-devel
Derived 'simple' in '%s/foo/devel/simple' from simple=/localhost@rpl:linux/1.0-1-1[]
Edit the recipe to add your changes to the binary package.
''' %(self.workDir))
        os.chdir('simple')
        state = open('CONARY').read()
        self.failIf('extrafile' in state,
                    'Extra files not removed from checkout')
        assert(os.path.exists('_ROOT_'))
        self.verifyFile('_ROOT_/some/file', 'contents\n')

    def testCheckoutNew(self):
        self.openRepository()
        self.addComponent('simple:source', 
                         [('simple.recipe', recipes.simpleRecipe)])
        self.addComponent('simple:runtime')
        self.addCollection('simple', [':runtime'])
        self.addCollection('group-dist', ['simple'])
        self.initProductDirectory('foo')
        os.chdir('foo/devel')
        txt = self.runCommand('checkout simple --new', stdin='Y\n')
        self.failUnlessEqual(txt, "Do you want to replace the upstream "
                    "version? (Y/N): (Default: Y): "
                "Created new package 'simple' in './simple'\n"
                "warning: Package simple exists upstream.\n")
        os.chdir('simple')
        assert('@NEW@' in open('CONARY').read())

    def testCheckoutNewTemplate(self):
        self.openRepository()
        self.addComponent('simple:source', 
                         [('simple.recipe', recipes.simpleRecipe)])
        self.addComponent('simple:runtime')
        self.addCollection('simple', [':runtime'])
        self.addCollection('group-dist', ['simple'])
        self.initProductDirectory('foo')
        os.chdir('foo/devel')
        #Do templates exist in the environment?
        txt = self.runCommand('checkout simple --new --template=default',
                               stdin='Y\n')
        self.failUnlessEqual(txt, "Do you want to replace the upstream "
                    "version? (Y/N): (Default: Y): "
                "Created new package 'simple' in './simple'\n"
                "warning: Package simple exists upstream.\n")
        os.chdir('simple')
        assert('@NEW@' in open('CONARY').read())
        self.assertEquals(open('simple.recipe').read(),'''#
# Copyright (c) %s Test (http://bugzilla.rpath.com/)
#

class Simple(PackageRecipe):
    name = 'simple'
    version = ''

    buildRequires = []

    def setup(r):
        pass
''' % time.localtime().tm_year)

    def testCheckoutTemplate(self):
        self.openRepository()
        self.initProductDirectory('foo')
        # bogus top level group with nothing relevant in it.
        self.addCollection('group-dist', ['simple:run'])
        os.chdir('foo/devel')
        txt = self.runCommand('checkout package --template=default')
        self.assertEquals(txt, "Created new package 'package' in './package'\n")
        os.chdir('package')
        assert('@NEW@' in open('CONARY').read())
        self.assertEquals(open('package.recipe').read(),'''#
# Copyright (c) %s Test (http://bugzilla.rpath.com/)
#

class Package(PackageRecipe):
    name = 'package'
    version = ''

    buildRequires = []

    def setup(r):
        pass
''' % time.localtime().tm_year)


