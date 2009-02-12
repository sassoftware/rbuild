#
# Copyright (c) 2006-2008 rPath, Inc.
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
rBuild-specific errors.
"""
import os
from conary.lib import util

# make ParseError available from here as well
# pylint: disable-msg=W0611
from conary.errors import ParseError


class RbuildBaseError(RuntimeError):
    """
    B{C{RbuildBaseError}} - Base class for all rBuild exceptions.

    New exceptions should derive from a subclass of this one, for
    example C{RbuildPluginError}.

    @cvar template: A template string used when displaying the
                    exception. Must use only keyword substitution.
    @cvar params: A list of parameter names used in the above template.
    """
    template = 'An unknown error has occurred'
    params = []

    def __init__(self, *args, **kwargs):
        RuntimeError.__init__(self)
        name = self.__class__.__name__

        # Sanity check
        for param in self.params:
            assert not hasattr(self.__class__, param), ("Parameter %r "
                    "conflicts with class dictionary, name it "
                    "something else." % param)
            assert param not in self.__dict__, ("Parameter %r "
                    "conflicts with instance dictionary, name it "
                    "something else." % param)

        self._values = dict()
        if kwargs:
            # Use keyword arguments
            if args:
                raise TypeError("Exception %s cannot take both positional "
                    "and keyword arguments" % name)

            missing = set(self.params) - set(kwargs)
            if missing:
                missingStr = ", ".join("%r" % x for x in missing)
                raise TypeError("Expected argument%s %s to exception %s" % (
                    len(missing) != 1 and 's' or '', missingStr, name))

            for key, value in kwargs.iteritems():
                if key not in self.params:
                    raise TypeError("Exception %s got an unexpected "
                        "argument %r" % (name, key))
                self._values[key] = value
        else:
            # Use positional arguments
            if len(self.params) != len(args):
                raise TypeError("Exception %s takes exactly %d argument%s "
                    "(%d given)" % (name, len(self.params),
                    len(self.params) != 1 and "s" or "", len(args)))

            for name, value in zip(self.params, args):
                self._values[name] = value

    def __getattr__(self, name):
        if name in self._values:
            return self._values[name]
        raise AttributeError(name)

    def __str__(self):
        return self.template % self._values

    def __repr__(self):
        params = ', '.join('%s=%r' % (x, self._values[x])
                for x in self.params)
        return '%s(%s)' % (self.__class__.__name__, params)


class RbuildInternalError(RbuildBaseError):
    """
    B{C{RbuildInternalError}} - superclass for all errors that are not meant to be
    seen.

    Errors deriving from InternalError should never occur, but when they do
    they indicate a failure within the code to handle some unexpected case.

    Do not raise this exception directly.
    """


class RbuildError(RbuildBaseError):
    """
    B{C{RbuildError}} - Internal rBuild errors

    This error may be raised only by rBuild internals, not by plugins.
    It may be raised directly but creating a new subclass for each
    specific case is recommended.
    """
    template = "%(msg)s"
    params = ['msg']


class PluginError(RbuildBaseError):
    """
    B{C{RbuildPluginError}} - rBuild plugin errors

    This error may be raised only by rBuild plugins, not by rBuild
    internals, and is the superclass for more specific errors raised
    by rBuild plugins. It may be raised directly but creating a new
    subclass for each specific case is recommended.
    """
    template = "%(msg)s"
    params = ['msg']


#Uncomment this, possibly modifying it, when we add deprecation
#infrastructure -- https://issues.rpath.com/browse/RBLD-147
#class DeprecatedInterfaceError(RbuildBaseError):
#    """
#    B{C{DeprecatedInterfaceError}} - Interface deprecated
#
#    This interface has been deprecated and may be removed in the
#    specified version.
#    """
#    Unsupportedtemplate = ('Deprecated interface %(name)s:'
#                           ' will be removed in rBuild %(version)s')
#    params = ['name', 'version' ]


class IncompleteInterfaceError(RbuildBaseError):
    """
    B{C{IncompleteInterfaceError}} - Interface unavailable in this configuration

    This error is raised by stub functions that are not filled in;
    for example, a function that makes sense only in the context
    of filesystem operations might raise this error if called in
    the context of repository operations.
    """
    template = "Unsupported interface: %(msg)s"
    params = ['msg']


class BadParameterError(RbuildBaseError):
    """
    Raised when a command is given bad parameters at the command line.
    """
    template = "%(msg)s"
    params = ['msg']


## BEGIN Internal Errors
class InvalidAPIMethodError(RbuildInternalError):
    "Raised when an unknown API method is referenced by an internal call."
    template = "No such API method %(method)r"
    params = ['method']


class InvalidHookReturnError(RbuildInternalError):
    "Raised when a prehook returns something unexpected."
    template = ("Invalid return value from prehook %(hook)r "
            "for function %(method)r")
    params = ['hook', 'method']


class MissingPluginError(RbuildInternalError):
    """
    Raised on attempts to access a plugin that is not known to the
    C{RbuildHandle} object.
    """
    template = "Plugin %(pluginName)r is not loaded"
    params = ['pluginName']

class InternalRmakeFacadeError(RbuildError):
    """
    Raised when rMake returns results that rBuild does not know how
    to interpret.
    """
    template = "Unexpected results from rMake: %(msg)r"
    params = ['msg']

## END Internal Errors


## BEGIN rBuild Errors
class MissingProductStoreError(RbuildError):
    template = "Directory %(path)r does not contain a product checkout"
    params = ['path']


class MissingGroupSearchPathElementError(RbuildError):
    template = ("Group search path element "
            "%(name)s=%(version)s[%(flavor)s] was not found")
    params = ['name', 'version', 'flavor']

class MissingImageDefinitionError(RbuildError):
    template = '\n'.join((
        'Product Definition %(name)s contains no image definitions',
        'Please add at least one image to your product definition'))
    params = ['name']

class RbuilderError(RbuildError):
    template = "rBuilder error %(error)s: %(frozen)r"
    params = ['error', 'frozen']

class RbuilderUserError(RbuilderError):
    template = 'Error retrieving user details: %(error)s: %(frozen)r'


## END rBuild Errors


#: error that is output when a Python exception makes it to the command 
#: line.
_ERROR_MESSAGE = '''
ERROR: An unexpected condition has occurred in rBuild.  This is
most likely due to insufficient handling of erroneous input, but
may be some other bug.  In either case, please report the error at
https://issues.rpath.com/ and attach to the issue the file
%(stackfile)s

To get a debug prompt, rerun the command with the --debug-all argument.

For more information, go to:
http://wiki.rpath.com/wiki/Conary:How_To_File_An_Effective_Bug_Report
For more debugging help, please go to #conary on freenode.net
or email conary-list@lists.rpath.com.

Error details follow:

%(filename)s:%(lineno)s
%(errtype)s: %(errmsg)s

The complete related traceback has been saved as %(stackfile)s
'''


def _findCheckoutRoot():
    """
    Find the top-level directory of the current checkout, if any.
    @return: directory name, or None if no checkout found
    """
    dirName = os.getcwd()
    for _ in range(dirName.count(os.path.sep)+1):
        if os.path.isdir(os.path.join(dirName, '.rbuild')):
            return dirName
        dirName = os.path.dirname(dirName)
    return None


def genExcepthook(*args, **kw):
    #pylint: disable-msg=C0999
    # just passes arguments through
    """
    Generates an exception handling hook that brings up a debugger.

    If the current working directory is underneath a product checkout,
    a full traceback will be output in
    C{<checkout root>/.rbuild/tracebacks/}, otherwise one will be
    output in C{/tmp}.

    Example::
        sys.excepthook = genExceptHook(debugAll=True)
    """

    #pylint: disable-msg=C0103
    # follow external convention
    def excepthook(e_type, e_value, e_traceback):
        """Exception hook wrapper"""
        checkoutRoot = _findCheckoutRoot()
        outputDir = None
        if checkoutRoot:
            #pylint: disable-msg=W0702
            # No exception type(s) specified - a generic handler is
            # warranted as this is in an exception handler.
            try:
                outputDir = checkoutRoot + '/.rbuild/tracebacks'
                if not os.path.exists(outputDir):
                    os.mkdir(outputDir, 0700)
                elif not os.access(outputDir, os.W_OK):
                    outputDir = None
            except:
                # fall back gracefully if we can't create the directory
                outputDir = None

        if outputDir:
            baseHook = util.genExcepthook(error=_ERROR_MESSAGE,
                prefix=outputDir + '/rbuild-error-', *args, **kw)
        else:
            baseHook = util.genExcepthook(error=_ERROR_MESSAGE,
                prefix='rbuild-error-', *args, **kw)

        baseHook(e_type, e_value, e_traceback)

    return excepthook


#pylint: disable-msg=C0103
# this shouldn't be upper case.
_uncatchableExceptions = (KeyboardInterrupt, SystemExit)
