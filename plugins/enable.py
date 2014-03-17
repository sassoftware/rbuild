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


from rbuild import errors
from rbuild import pluginapi
from rbuild.pluginapi import command


class EnablePlatformCommand(command.BaseCommand):
    help = 'Enable or disable a platform'
    commands = ['enable', 'disable']
    paramHelp = '<LABEL>'

    def runCommand(self, handle, argSet, args):
        command, label = self.requireParameters(args, expected='LABEL')

        if command == 'disable':
            handle.EnablePlatform.disable(label)
        elif command == 'enable':
            handle.EnablePlatform.enable(label)


class EnablePlatform(pluginapi.Plugin):
    name = 'enable'

    def _updatePlatform(self, label, enabled):
        platform = self.handle.facade.rbuilder.getPlatform(label)
        if platform is None:
            raise errors.PluginError(
                "No platform with label matching: '%s'" % label)
        platform.enabled = enabled
        platform.persist()

    def disable(self, label):
        self._updatePlatform(label, enabled=False)

    def enable(self, label):
        self._updatePlatform(label, enabled=True)

    def registerCommands(self):
        self.handle.Commands.registerCommand(EnablePlatformCommand)
