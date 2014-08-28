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


"""
decorators
"""
import functools
import os

from rbuild import errors
from rbuild.handle import RbuildHandle


def _getHandle(l):
    if hasattr(l[0], 'handle') \
            and isinstance(l[0].handle, RbuildHandle):
        _handle = l[0].handle
    elif isinstance(l[1], RbuildHandle):
        _handle = l[1]
    else:
        raise errors.PluginError("Must wrap a plugin methodor the runCommand"
                                 " method of a BaseCommand subclass")
    return _handle


def requiresProduct(method):
    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        _handle = _getHandle(args)
        if _handle.productStore is None:
            raise errors.MissingProductStoreError(os.getcwd())
        return method(*args, **kwargs)
    return wrapper


def requiresStage(method):
    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        _handle = _getHandle(args)
        if _handle.productStore is None:
            raise errors.MissingProductStoreError(os.getcwd())
        if _handle.productStore._currentStage is None:
            raise errors.MissingActiveStageError(os.getcwd())
        return method(*args, **kwargs)
    return wrapper
