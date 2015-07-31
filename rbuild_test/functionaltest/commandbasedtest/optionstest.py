#!/usr/bin/python
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



import re

from rbuild_test import rbuildhelp

class ConfigFileTest(rbuildhelp.CommandTest):
    def testConfigFileDoesntExist(self):
        txt = self.runCommand('--config-file /tmp/doesntexist/foo init', exitCode=1)
        assert(re.match(r'error: Error reading config file', txt))
        assert(re.search(r'No such file or directory', txt))
        assert(re.search(r'/tmp/doesntexist/foo', txt))
