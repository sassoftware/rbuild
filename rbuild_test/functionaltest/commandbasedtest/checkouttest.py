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

from StringIO import StringIO
import difflib
import os
import sys
import time

from conary.lib import util
from conary_test import recipes

from rbuild_test import rbuildhelp


class CheckoutTest(rbuildhelp.CommandTest):

    def assertEquals(self, v1, v2):
        try:
            rbuildhelp.CommandTest.assertEquals(self, v1, v2)
        except AssertionError:
            for line in difflib.unified_diff(
                    StringIO(v1).readlines(),
                    StringIO(v2).readlines(),
                    "v1",
                    "v2",
                    ):
                sys.stdout.write(line)
            raise

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
        self.assertEquals(open('simple.recipe').read(),'''\
#
# Copyright (c) %s Test (http://bugzilla.rpath.com/)
#

class Simple(PackageRecipe):
    name = 'simple'
    version = ''

    buildRequires = []

    def setup(r):
        pass
''' % time.localtime().tm_year)

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
        txt = self.runCommand('checkout simple --new --template=rpath',
                               stdin='Y\n')
        self.failUnlessEqual(txt, "Do you want to replace the upstream "
                    "version? (Y/N): (Default: Y): "
                "Created new package 'simple' in './simple'\n"
                "warning: Package simple exists upstream.\n")
        os.chdir('simple')
        assert('@NEW@' in open('CONARY').read())
        self.assertEquals(open('simple.recipe').read(),'''\
#
# Copyright (c) %s rPath, Inc.
# This file is distributed under the terms of the MIT License.
# A copy is available at http://www.rpath.com/permanent/mit-license.html
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
        txt = self.runCommand('checkout package --template=rpath')
        self.assertEquals(txt, "Created new package 'package' in './package'\n")
        os.chdir('package')
        assert('@NEW@' in open('CONARY').read())
        self.assertEquals(open('package.recipe').read(),'''\
#
# Copyright (c) %s rPath, Inc.
# This file is distributed under the terms of the MIT License.
# A copy is available at http://www.rpath.com/permanent/mit-license.html
#

class Package(PackageRecipe):
    name = 'package'
    version = ''

    buildRequires = []

    def setup(r):
        pass
''' % time.localtime().tm_year)

    def testCheckoutGroup(self):
        self.openRepository()
        self.initProductDirectory('foo')
        # bogus top level group with nothing relevant in it.
        self.addCollection('group-dist', ['simple:run'])
        os.chdir('foo/devel')
        txt = self.runCommand('checkout group-foo')
        self.assertEquals(txt, "Created new package 'group-foo' in './group-foo'\n")
        os.chdir('group-foo')
        assert('@NEW@' in open('CONARY').read())
        self.assertEquals(open('group-foo.recipe').read(),"""\
#
# Copyright (c) %s Test (http://bugzilla.rpath.com/)
#

class GroupFoo(GroupSetRecipe):
    name = 'group-foo'
    version = ''

    checkPathConflicts = True
    depCheck = True
    imageGroup = True

    # packages to be added to group
    packages = []

    def makeSearchPath(r):
        '''
        Constructs a search path using the buildLabel and the product
        definition, if available. If additional search paths are required,
        add them to the sps list below
        '''
        # add additional search paths
        sps = []

        buildLabel = r.cfg.buildLabel
        repo = r.Repository(buildLabel, r.flavor)
        if 'productDefinitionSearchPath' in r.macros:
            for specs in r.macros.productDefinitionSearchPath.split('\\n'):
                if isinstance(specs, basestring):
                    specs = [specs]
                sps.append(repo.find(*specs))
        return r.SearchPath(repo, *sps)

    def setup(r):
        sp = r.makeSearchPath()

        packages = sp.find(*r.packages)

        if r.depCheck:
            # Checks against upstream searchpaths
            deps = packages.depsNeeded(sp)

            if r.imageGroup:
                # For a bootable image (hopefully)
                packages += deps

        r.Group(packages, checkPathConflicts=r.checkPathConflicts)
""" % time.localtime().tm_year)

    def testCheckoutGroupAppliance(self):
        self.openRepository()
        self.initProductDirectory('foo')
        # bogus top level group with nothing relevant in it.
        self.addCollection('group-dist', ['simple:run'])
        os.chdir('foo/devel')
        txt = self.runCommand('checkout group-foo-appliance')
        self.assertEquals(txt, "Created new package 'group-foo-appliance' in './group-foo-appliance'\n")
        os.chdir('group-foo-appliance')
        assert('@NEW@' in open('CONARY').read())
        self.assertEquals(open('group-foo-appliance.recipe').read(), '''\
#
# Copyright (c) %s Test (http://bugzilla.rpath.com/)
#

loadSuperClass("group-set-appliance=centos6.rpath.com@rpath:centos-6-common")
class GroupFooAppliance(GroupSetAppliance):
    name = "group-foo-appliance"
    version = ""

    buildRequires = []

    # add additional search path groups here
    additionalSearchPath = []

    def addPackages(r):
        """
        Here is where you define your appliance by manipulating the
        packages included in the appliance and scripts that are run.

        Packages may be added, removed or replaced

            Add application packages by calling r.add("pkgname")

            Remove packages from the appliance by calling r.remove("pkgname")

            Replace upstream packages by calling r.replace("pkgname")

        Scripts may be added by calling the appropriate method with the
        text of the script. The available methods are:

            r.addPostInstallScript(txt)
            r.addPostUpdateScript(txt)
            r.addPostRollbackScript(txt)
            r.addPreInstallScript(txt)
            r.addPreUpdateScript(txt)
            r.addPreRollbackScript(txt)
        """
        pass
''' % time.localtime().tm_year)
