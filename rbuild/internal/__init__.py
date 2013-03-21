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
The rBuild Appliance Developer Process Toolkit Internal Interfaces

The C{rbuild.internal} modules provide private internal interfaces
used internally in rBuild, including implementation of features
for which public APIs are included in the main C{rbuild} module.
These interfaces may change completely between minor releases
of rBuild.  No rBuild plugin should consume or otherwise use any
interfaces from C{rbuild.internal}.
"""
