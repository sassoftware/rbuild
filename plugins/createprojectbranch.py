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


class CreateProjectCommand(command.BaseCommand):
    help = 'Create a project on SAS App Engine'
    docs = {
            'name': 'Long name (title) of project',
            'short-name': 'Short (unique) name of project',
            'domain-name': 'Domain name of project, or default if omitted',
            'description': 'Optional description for the project',
      }

    def addLocalParameters(self, argDef):
        argDef['name'] = command.ONE_PARAM
        argDef['short-name'] = command.ONE_PARAM
        argDef['domain-name'] = command.ONE_PARAM
        argDef['descrption'] = command.ONE_PARAM

    def runCommand(self, handle, argSet, args):
        ui = handle.ui
        rb = handle.facade.rbuilder
        if not argSet.get('name'):
            argSet['name'] = ui.getResponse("Project name")
            argSet['description'] = ui.input("Project description (optional): ")
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
                description=argSet.get('description', ''),
                )
        ui.info("Created project %s", projectId)


class CreateBranchCommand(command.BaseCommand):
    help = 'Create a branch within an existing project'
    docs = {
            'project': 'Short (unique) name of the existing project',
            'branch': 'Version or name of the new branch',
            'namespace': 'Optional namespace for the new branch',
            'description': 'Optional description for the new branch',
            'platform': 'Platform href, label, or name on which to base the new branch',
      }

    def addLocalParameters(self, argDef):
        argDef['project'] = command.ONE_PARAM
        argDef['branch'] = command.ONE_PARAM
        argDef['namespace'] = command.ONE_PARAM
        argDef['description'] = command.ONE_PARAM
        argDef['platform'] = command.ONE_PARAM

    def runCommand(self, handle, argSet, args):
        ui = handle.ui
        rb = handle.facade.rbuilder
        if not argSet.get('project'):
            argSet['project'] = ui.getResponse("Project name",
                    validationFn=rb.isValidShortName)
        if not argSet.get('branch'):
            argSet['branch'] = ui.getResponse("Branch name",
                    validationFn=rb.isValidBranchName)
            argSet['description'] = ui.input("Branch description (optional): ")
            argSet['namespace'] = ui.input("Namespace (blank for default): ")
        platforms = rb.listPlatforms()
        if argSet.get('platform'):
            match = argSet['platform'].lower().strip()
            platformLabel = None
            for platform in platforms:
                for value in (platform.platformName, platform.label,
                        platform.id):
                    if value.lower().strip() == match:
                        platformLabel = platform.label
                        break
                if platformLabel is not None:
                    break
            if platformLabel is None:
                raise errors.PluginError("No platform matching term '%s' "
                        "was found" % (argSet['platform'],))
        else:
            display = ['%s - %s' % (x.platformName, x.label) for x in platforms]
            response = ui.getChoice("Platform", display,
                    "The following platforms are available:")
            platformLabel = platforms[response].label
        label = rb.createBranch(
                project=argSet['project'],
                name=argSet['branch'],
                platformLabel=platformLabel,
                namespace=argSet.get('namespace'),
                description=argSet.get('description', ''),
                )
        ui.info("Created branch on label %s", label)
        ui.info("Type 'rbuild init %s %s' to begin working with it",
                argSet['project'], argSet['branch'])


class CreateProjectBranch(pluginapi.Plugin):

    def initialize(self):
        cmd = self.handle.Commands.getCommandClass('create')
        cmd.registerSubCommand('project', CreateProjectCommand)
        cmd.registerSubCommand('branch', CreateBranchCommand)
