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
The rBuild Appliance Developer Process Toolkit Facades

The C{rbuild.facade} modules provide public facades for lower-level
rPath APIs.  These facades are intended to be APIs that are:
 - High-level: do not require many lines of boilerplate to accomplish
   an action.
 - Very stable: when underlying APIs are modified, only the facade
   should need to be adapted, not the plugins that use the facade.

These APIs will be backward-compatible within major versions of rBuild.

Module functions, classes, and class methods that do not start
with a C{_} character are public.
"""
