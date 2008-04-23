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
The rBuild Appliance Developer Process Toolkit Internal Interfaces

The C{rbuild.internal} modules provide private internal interfaces
used internally in rBuild, including implementation of features
for which public APIs are included in the main C{rbuild} module.
These interfaces may change completely between minor releases
of rBuild.  No rBuild plugin should consume or otherwise use any
interfaces from C{rbuild.internal}.
"""
