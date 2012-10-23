#
# Copyright (c) rPath, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#


"""
Types used internally by the rBuild implementation.

As with all internal components, these interfaces are subject to
change.
"""

import weakref


def findPropCaller(descr, othercls):
    """
    Figure out what attribute of class C{othercls} a descriptor
    C{descr} is stored in.

    C{othercls} and its entire method-resolution order will be
    searched.

    NOTE: Never store multiple copies of the same instance of any
    descriptor, especially ones that use this function. If you do,
    this function will probably return the wrong name!

    @param descr: Descriptor to locate
    @type  descr: C{object}
    @param othercls: Class in which to find C{descr}
    @type  othercls: C{type}
    """

    for cls in othercls.mro():
        for key, value in cls.__dict__.iteritems():
            if value is descr:
                return key

    # Nothing in the object's MRO references this descriptor.
    raise AssertionError("invalid descriptor call")


class AttributeHook(object):
    """
    A property descriptor that "hooks" all assignments.

    Before an assignment, a method is invoked on the new value (if it
    is not C{None}), with the parent object as the only argument.

    Attribute fetches are passed through. Deletions will assign C{None}.

    This is a data descriptor.

    @param attribute: The attribute to invoke on the new value before
                      the assignment is performed.
    @type  attribute: C{basestring}
    """

    __slots__ = ['attribute']

    def __init__(self, attribute):
        self.attribute = attribute

    def _attr(self, cls):
        """
        Get the called attribute name.

        @param cls: Owner class
        """
        return findPropCaller(self, cls)

    def __get__(self, obj, cls):
        """
        Pass-through; should behave identically to a descriptorless fetch.
        """
        prop = self._attr(cls)
        if obj:
            return obj.__dict__.get(prop, None)
        else:
            return self

    def __set__(self, obj, value):
        """
        If C{value} is not C{None}, invoke a pre-hook on that value.
        """
        if value is not None:
            getattr(value, self.attribute)(obj)

        prop = self._attr(type(obj))
        obj.__dict__[prop] = value

    def __delete__(self, obj):
        """
        Assign C{None}.
        """
        prop = self._attr(type(obj))
        obj.__dict__[prop] = None


class WeakReference(object):
    """
    A property descriptor that transparently weak references its value.

    Upon assignment, a weak reference is created, and further accesses
    dereference it automatically. The default value is always C{None}.

    The generated weak reference can be accessed by appending "_ref" to
    the name this descriptor is assigned to, though only after an
    assignment has been performed. Consequently, if slots are in use
    in the owning class, a slot will need to be added with this name.

    This is a data descriptor.
    """

    __slots__ = []

    def _attr(self, cls):
        """
        Return the name used to stow the reference itself in the
        owner's dictionary.

        @param cls: Owner class
        """
        return findPropCaller(self, cls) + '_ref'

    def __get__(self, obj, cls):
        """
        If the stored reference exists and is not C{None}, de-reference
        it and return that value. Otherwise, return C{None}.
        """
        if obj:
            prop = self._attr(cls)
            ref = obj.__dict__.get(prop, None)
            if ref:
                return ref()
            else:
                return None
        else:
            # Pass-through
            return self

    def __set__(self, obj, value):
        """
        Store a weak reference to C{value}, or C{None} if C{value} is
        C{None}.
        """
        if value is not None:
            value = weakref.ref(value)
        prop = self._attr(type(obj))
        obj.__dict__[prop] = value

    def __delete__(self, obj):
        """
        Assign C{None}.
        """
        prop = self._attr(type(obj))
        obj.__dict__[prop] = None
