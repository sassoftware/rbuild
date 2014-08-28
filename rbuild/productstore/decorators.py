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
from rbuild.pluginapi import Plugin


def _getHandle(args):
    """
    Search `args` for a handle.

    If the first item in `args` is a Plugin, then return the Plugin's handle.
    Else if the second item in `args` is a RbuildHandle, then return it.

    :param list args: list to search
    :return RbuildHandle: a handle
    """
    if isinstance(args[0], Plugin):
        return args[0].handle
    elif isinstance(args[1], RbuildHandle):
        return args[1]
    else:
        raise errors.PluginError("Must wrap a plugin method or the runCommand"
                                 " method of a BaseCommand subclass")


def requiresProduct(method):
    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        handle = _getHandle(args)
        if handle.productStore is None:
            raise errors.MissingProductStoreError(os.getcwd())
        return method(*args, **kwargs)
    return wrapper


def requiresStage(method):
    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        handle = _getHandle(args)
        if handle.productStore is None:
            raise errors.MissingProductStoreError(os.getcwd())
        if handle.productStore._currentStage is None:
            raise errors.MissingActiveStageError(os.getcwd())
        return method(*args, **kwargs)
    return wrapper
