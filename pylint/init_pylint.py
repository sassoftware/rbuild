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
