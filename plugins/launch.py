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

import time

from xobj import xobj

from rbuild import errors
from rbuild import pluginapi
from rbuild.pluginapi import command


class LaunchCommand(command.BaseCommand):
    help = 'Launch/Deploy an image onto a target'
    paramHelp = '<IMAGE> <TARGET>'
    commands = ['launch', 'deploy']
    docs = {'list': 'List available targets',
            'from-file': 'Load launch/deploy descriptor from file',
            'to-file': 'Write launch/deploy descriptor to file',
            'no-watch': 'Do not wait for job to complete',
            }

    def addLocalParameters(self, argDef):
        argDef['list'] = '-l', command.NO_PARAM
        argDef['from-file'] = '-f', command.ONE_PARAM
        argDef['to-file'] = '-o', command.ONE_PARAM
        argDef['no-watch'] = command.NO_PARAM

    def runCommand(self, handle, argSet, args):
        ui = handle.ui
        rb = handle.facade.rbuilder

        listTargets = argSet.pop('list', False)
        fromFile = argSet.pop('from-file', None)
        toFile = argSet.pop('to-file', None)
        watch = not argSet.pop('no-watch', False)

        if listTargets:
            ui.write('Available targets: %s' %
                     ', '.join(t.name for t in rb.getEnabledTargets()))
            return

        if fromFile:
            handle.DescriptorConfig.readConfig(fromFile)

        command, image, target = self.requireParameters(
            args, expected=['IMAGE', 'TARGET'])

        if command == 'deploy':
            job = handle.Launch.deployImage(image, target)
        else:
            job = handle.Launch.launchImage(image, target)

        if watch:
            handle.Launch.watchJob(job)

        if toFile:
            handle.DescriptorConfig.writeConfig(toFile)


class Launch(pluginapi.Plugin):
    name = 'launch'
    DEPLOY = 'deploy_image_on_target'
    LAUNCH = 'launch_system_on_target'

    def _createJob(self, image_name, target_name, action_type):
        rb = self.handle.facade.rbuilder

        product, stage = self._getProductStage()
        image_name, _, version = image_name.partition('=')
        image = rb.getImage(
            image_name,
            shortName=product,
            stageName=stage,
            trailingVersion=version,
            )

        action = self._getAction(image, target_name, action_type)

        ddata = self.handle.DescriptorConfig.createDescriptorData(
            fromStream=action.descriptor)

        doc = xobj.Document()
        doc.job = job = xobj.XObj()

        job.job_type = action._root.job_type
        job.descriptor = action._root.descriptor
        job.descriptor_data = xobj.parse(ddata.toxml()).descriptor_data

        return image.jobs.append(doc)

    def _getAction(self, image, target, key):
        assert key in (self.DEPLOY, self.LAUNCH)

        for action in image.actions:
            if key == action.key and target in action.name:
                return action
        raise errors.PluginError(
            'Image cannot be %s on this target' %
            ('deployed' if key == self.DEPLOY else 'launched'))

    def _getProductStage(self):
        try:
            product = self.handle.product.getProductShortname()
        except AttributeError:
            raise errors.PluginError(
                'Current directory is not part of a product.\n'
                'To initialize a new product directory, use "rbuild init"')

        try:
            stage = self.handle.productStore.getActiveStageName()
        except errors.RbuildError:
            raise errors.PluginError(
                'Current directory is not a product stage.')
        return (product, stage)

    def registerCommands(self):
        self.handle.Commands.registerCommand(LaunchCommand)

    def deployImage(self, image, target):
        '''
        Deploys an image template to a target

        @param image: name of image to deploy
        @type image: str
        @param target: name of target to deploy to
        @type target: str
        @param config: deploy configuration data
        @type config: dict
        @return: image deploy job
        @rtype: rObj(job)
        '''
        return self._createJob(image, target, self.DEPLOY)

    def launchImage(self, image, target):
        '''
        Launches an image to a target

        @param image: name of image to deploy
        @type image: str
        @param target: name of target to launch to
        @type target: str
        @param config: deploy configuration data
        @type config: dict
        @return: image launch job
        @rtype: rObj(job)
        '''
        return self._createJob(image, target, self.LAUNCH)

    def watchJob(self, job):
        last_status = None
        while job.job_state.name in ['Queued', 'Running']:
            status = job.status_text
            if status != last_status:
                self.handle.ui.lineOutProgress(status.replace('%', '%%'))
            last_status = status
            time.sleep(1)
            job.refresh()

        if job.job_state.name == 'Failed':
            raise errors.PluginError(job.status_text)

        if self.handle.ui.outStream.isatty():
            self.handle.ui.write()

        if job.job_type.name.startswith('launch'):
            for resource in job.created_resources:
                if hasattr(resource, 'networks'):
                    msg = 'Created system %s with address' % resource.name
                    if len(resource.networks) > 1:
                        msg += 'es'
                    msg += ': '
                    msg += ', '.join(n.dns_name for n in resource.networks)
                    self.handle.ui.write(msg)
