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



import weakref
from rbuild.internal import internal_types
from testutils import mock

from rbuild_test import rbuildhelp


class Foo(object):
    bar = internal_types.WeakReference()
    baz = internal_types.AttributeHook('do_it')


class TypesTest(rbuildhelp.RbuildHelper):
    def testWeakReference(self):
        foo = Foo()

        # Default
        self.assertEqual(foo.bar, None)

        # Set
        bar = mock.MockObject()
        foo.bar = bar
        self.assertEqual(foo.bar, bar)
        self.assertEqual(type(foo.__dict__['bar_ref']), weakref.ref)

        # Reset
        foo.bar = None
        self.assertEqual(foo.bar, None)
        self.assertEqual(foo.__dict__['bar_ref'], None)

        # Delete
        del foo.bar
        self.assertEqual(foo.bar, None)
        self.assertEqual(foo.__dict__['bar_ref'], None)

    def testWeakReferenceClass(self):
        self.assertEqual(Foo.bar, Foo.__dict__['bar'])

    def testAttributeHook(self):
        foo = Foo()

        # Default
        self.assertEqual(foo.baz, None)

        # Set
        baz = mock.MockObject()
        foo.baz = baz
        baz.do_it._mock.assertCalled(foo)
        self.assertEqual(foo.baz, baz)

        # Set (bad)
        baz2 = object()
        try:
            foo.baz = baz2
        except AttributeError:
            pass
        else:
            self.fail('Assignment of object should have failed')
        # Old value should remain
        self.assertEqual(foo.baz, baz)

        # Reset
        foo.baz = None
        self.assertEqual(foo.baz, None)

        # Delete
        del foo.baz
        self.assertEqual(foo.baz, None)

    def testAttributeHookClass(self):
        self.assertEqual(Foo.baz, Foo.__dict__['baz'])

    def testInvalidCall(self):
        """
        Using a descriptor that does not appear anywhere in the MRO of
        the parent object should fail.
        """
        descr = internal_types.WeakReference()
        obj = Foo()
        self.assertRaises(AssertionError, descr.__get__, obj, Foo)


