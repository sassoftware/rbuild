# rBuild -- Archived Repository
**Notice: This repository is part of a Conary/rpath project at SAS that is no longer supported or maintained. Hence, the repository is being archived and will live in a read-only state moving forward. Issues, pull requests, and changes will no longer be accepted.**

INTRODUCTION
============

rBuild is the unified interface for Conary, rMake, and rBuilder.
The purpose of this tool is to provide a single, unified, and
fully-documented interface (command line and Python API) to
developers using rPath technologies, using an extensible plugin
framework, which automates many of the steps required to follow
rPath's recommended best practices.

rBuild depends on product-definition packages that define the
characteristics of the product you are building, including which
images you build, what platform your product is based on, and
so forth.  Use the rBuilder interface to create and edit these
packages.  rBuild updates them automatically when appropriate.

A shell script written using the command-line interface should be
relatively easy to transform to a Python program that uses the Python
API.  You can provide your own plugins that dynamically extend that
command-line interface and Python API.  Your plugins can also hook
into other parts of the API, allowing you to enforce preconditions
and take action following successful actions.


DEVELOPMENT
===========

Versions 1.x are focused on the command line.  Public python
APIs will be generally stable and will not be changed without
specific reason, but strong API stability will not be maintained.
API changes will be documented in the NEWS file for versions 1.x

It is currently intended that when version 2.0 is released, public
interfaces will be kept stable.  The general rule is that API
stability allows making changes that should be backward-compatible
in well-formed Python code.  For rBuild, "stable" is defined as:
 *  Adding optional keyword parameters is acceptable.
 *  Adding additional methods, classes, and functions is
    acceptable.
 *  Raising a more specific error class is acceptable, as
    long as the more specific error class is a subclass of
    the error previously raised.
 *  Modifying the semantics of existing arguments is not
    acceptable, except to extend them in ways that are
    generally functionally compatible.

The general exception is that if a significant functional bug
cannot be fixed without an interface change, the interface may
be changed (and the change noted in the NEWS file), and we will
make our best effort to mitigate the effects of the change.

All documentation regarding stable interfaces is relevant
only to published stable releases; it is not in force for alpha
and beta releases, including 0.x releases and any automated builds.

When interfaces are deprecated, the deprecated interface will be
supported for a major release cycle when feasible.  That is, if an
interface is deprecated during 2.x releases after 2.0 is released,
it will be available during 3.x releases, and may be removed starting
with 4.0.  During 3.x, it will be possible to request that that
API will raise rbuild.errors.DeprecatedInterfaceError; otherwise,
the APIs will provide a warning (printed to standard error in the
command-line use case).

API documentation is available at http://cvs.rpath.com/rbuild-docs/
or by running "make html" and viewing docs/developer/index.html (requires
epydoc).


Pylint Hooks
============

When developing rbuild and rbuild plugins, please consider using our
pylint commit hook.  This hook will run pylint against the files
you modified in your commit and warn you of any pylint problems.
Add the following lines to the file .hg/hgrc in your rbuild checkout:

[hooks]
precommit=./pylint/pylint_commit

Pylint problems that were caused by your patch should either be fixed
or disabled by adding a pylint pragma line.  The pylint pragma line
should look like this:

# W0611: unused variable ParseError - we want ParseError to be importable from
# errors.py even though it is not used.
# W0612: some other warning - reason why this warning is not being heeded
# pylint: disable-msg=W0611,W0612


REPORTING BUGS
==============

Please visit https://issues.rpath.com/ and file issues in the rBuild
project.
