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

import os
import sys
sys.path.insert(0, os.environ['CONARY_PATH'])
sys.path.insert(0, os.environ['RMAKE_PATH'])
sys.path.insert(0, os.environ['RBUILD_PATH'])
sys.path.insert(0, os.environ['PRODUCT_DEFINITION_PATH'])

from rbuild.internal import pluginloader
pluginDir = os.path.realpath(os.environ['RBUILD_PATH'] + '/plugins')
plugins = pluginloader.getPlugins([], [pluginDir])
plugins.loader.install()
