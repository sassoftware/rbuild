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
from testutils.module_utils import path_for_module


def get_path(*subpath):
    return os.path.join(_code_root, *subpath)


def get_test_path(*subpath):
    return os.path.join(_test_root, *subpath)


def get_archive(*subpath):
    return get_test_path('rbuild_test', 'archive', *subpath)


_code_root = path_for_module('rbuild')
_test_root = path_for_module('rbuild_test')


def get_plugin_dirs():
    if 'site-packages' in _code_root:
        return ['/usr/share/rbuild/plugins']
    else:
        return [os.path.join(_code_root, 'plugins')]
