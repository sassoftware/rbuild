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
Types used internally by the rBuild implementation.

As with all internal components, these interfaces are subject to
change.
"""

import weakref


def findPropCaller(descr, othercls):
    """
    Figure out what attribute a descriptor was accessed as.

    NOTE: When using a descriptor that utilizes this function, never
    use the same instance of the descriptor for multiple attributes,
    or this function will return the wrong name!

    @param descr: Descriptor to find the binding for
    @param othercls: Class whose MRO will be searched
    """

    for cls in othercls.__mro__:
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
