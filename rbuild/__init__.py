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
The rBuild Appliance Developer Process Toolkit

The C{rbuild} modules provide public interfaces for rBuild.
These interfaces will be backward-compatible within major
versions of rBuild, for certain versions of rBuild.  See
the README for more details on interface compatibility.

Module functions, classes, and class methods that do not start
with a C{_} character are public.

See the documentation for API versions that are imported into
this namespace for use of those APIs.

@group Plugin API: pluginapi
@group Internal Interfaces: internal
"""

from rbuild.api1 import *
