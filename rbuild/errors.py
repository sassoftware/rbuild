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

class InternalError(Exception):
    """
    B{C{InternalError}} - superclass for all errors that are not meant to be
    seen.

    Errors deriving from InternalError should never occur, but when they do
    they indicate a failure within the code to handle some unexpected case.
    """

class BaseError(Exception):
    """
    B{C{BaseError}} - superclass for all well-defined errors.

    If you create an error in rBuild, it should derive from this class,
    and have a str() that is acceptable output for the command line,
    with the string "C{error: }" prepended to it.

    Any relevant data for this error should be stored outside of the
    string so it can be accessed from non-command-line interfaces.
    """

class RbuildError(BaseError):
    """
    B{C{RbuildError}} - Internal rBuild errors

    This error may be raised directly only by rBuild internals,
    not by plugins.
    """

class PluginError(BaseError):
    """
    B{C{PluginError}} - rBuild plugin errors

    This error may be raised directly only by rBuild plugins,
    not by rBuild internals, and is the subclass for more
    specific errors raised by rBuild plugins.
    """

class IncompleteInterfaceError(BaseError):
    """
    B{C{IncompleteInterfaceError}} - Interface unavailable in this configuration

    This error is raised by stub functions that are not filled in;
    for example, a function that makes sense only in the context
    of filesystem operations might raise this error if called in
    the context of repository operations.
    """

class BadParameterError(BaseError):
    """
    Raised when a command is given bad parameters at the command line.
    """


class MissingPluginError(InternalError):
    """
    Raised on attempts to access a plugin that is not known to the
    C{RbuildHandle} object.
    """
    def __init__(self, pluginName):
        InternalError.__init__(self)
        self.pluginName = pluginName
    def __str__(self):
        return "Plugin %r is not loaded" % self.pluginName


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
        checkoutRoot = _findCheckoutRoot()
        outputDir = None
        if checkoutRoot:
            try:
                outputDir = checkoutRoot + '/.rbuild/tracebacks'
                if not os.path.exists(outputDir):
                    os.mkdir(outputDir, 0700)
                elif not os.access(outputDir, os.W_OK):
                    outputDir = None
            except:
                # fall back gracefully if we can't create the directory
                #pylint: disable-msg=W0702
                # don't really need to handle specific exceptions here
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
