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


from rbuild import pluginapi
from rbuild.pluginapi import command


class CreateProjectCommand(command.BaseCommand):
    help = 'Create a project on SAS App Engine'
    docs = {
            'name': 'Long name (title) of project',
            'short-name': 'Short (unique) name of project',
            'domain-name': 'Domain name of project, or default if omitted'
      }

    def addLocalParameters(self, argDef):
        argDef['name'] = command.ONE_PARAM
        argDef['short-name'] = command.ONE_PARAM
        argDef['domain-name'] = command.ONE_PARAM

    def runCommand(self, handle, argSet, args):
        ui = handle.ui
        rb = handle.facade.rbuilder
        if not argSet.get('name'):
            argSet['name'] = ui.getResponse("Project name")
        if not argSet.get('short-name'):
            argSet['short-name'] = ui.getResponse("Unique name",
                    validationFn=rb.isValidShortName)
        if 'domain-name' not in argSet:
            while True:
                argSet['domain-name'] = ui.input(
                        "Domain name (blank for default): ")
                if rb.isValidDomainName(argSet['domain-name']):
                    break
        projectId = rb.createProject(
                title=argSet['name'],
                shortName=argSet['short-name'],
                domainName=argSet.get('domain-name'),
                )
        ui.info("Created project %s", projectId)


class CreateProjectBranch(pluginapi.Plugin):

    def initialize(self):
        cmd = self.handle.Commands.getCommandClass('create')
        cmd.registerSubCommand('project', CreateProjectCommand)
