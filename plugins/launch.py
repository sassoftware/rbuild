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

from smartform import descriptor, descriptor_errors
import yaml

from rbuild import errors
from rbuild import pluginapi
from rbuild.facade.rbuilderfacade import RbuilderCallback
from rbuild.pluginapi import command
from xobj import xobj


DEPLOY = 'deploy_image_on_target'
LAUNCH = 'launch_image_on_target'


class LaunchCommand(command.BaseCommand):
    help = 'Launch/Deploy an image onto a target'
    paramHelp = '<IMAGE> <TARGET>'
    commands = ['launch', 'deploy']
    docs = {'list': 'List available targets',
            'from-file': 'Load launch/deploy descriptor from yaml file',
            'no-watch': 'Do not wait for job to complete',
            'deploy-only': 'Deploy image template but do not launch system',}

    def addLocalParameters(self, argDef):
        argDef['list'] = '-l', command.NO_PARAM
        argDef['from-file'] = '-f', command.ONE_PARAM
        argDef['no-watch'] = command.NO_PARAM

    def runCommand(self, handle, argSet, args):
        ui = handle.ui
        rb = handle.facade.rbuilder

        list_targets = argSet.pop('list', False)
        config_file = argSet.pop('from-file', None)
        watch = not argSet.pop('no-watch', False)

        if list_targets:
            ui.write('Available targets: %s' %
                     ', '.join(t.name for t in rb.getEnabledTargets()))
            return

        if config_file:
            with open(config_file) as fh:
                config = yaml.safe_load(fh)
        else:
            config = {}

        command, image_name, target_name = self.requireParameters(
            args, expected=['IMAGE', 'TARGET'])

        if command == 'deploy':
            job = handle.Launch.deployImage(image_name, target_name, config)
        else:
            job = handle.Launch.launchImage(image_name, target_name, config)

        if watch:
            handle.Launch.watchJob(job)


class Launch(pluginapi.Plugin):
    name = 'launch'

    def registerCommands(self):
        self.handle.Commands.registerCommand(LaunchCommand)

    def deployImage(self, image, target, config):
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
        return self._createJob(image, target, config, DEPLOY)

    def launchImage(self, image, target, config):
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
        return self._createJob(image, target, config, LAUNCH)

    def _createDescriptorData(self, descriptor, config):
        cb = RbuilderCallback(self.handle.ui, config)
        try:
            return descriptor.createDescriptorData(cb)
        except descriptor_errors.ConstraintsValidationError as e:
            raise errors.RbuildError('\n'.join(m for m in e[0]))

    def _createJob(self, image_name, target_name, config, atype):
        rb = self.handle.facade.rbuilder

        image = rb.getImageByName(image_name)

        action = self._getAction(image, target_name, atype)

        ddata = self._createDescriptorData(
            descriptor.ConfigurationDescriptor(fromStream=action.descriptor),
            config,
            )

        doc = xobj.Document()
        doc.job = job = xobj.XObj()

        job.job_type = action._root.job_type
        job.descriptor = action._root.descriptor
        job.descriptor_data = xobj.parse(ddata.toxml()).descriptor_data

        return image.jobs.append(doc)

    def _getAction(self, image, target, key):
        assert key in (DEPLOY, LAUNCH)

        for action in image.actions:
            if key == action.key and target in action.name:
                return action
        raise errors.RbuildError(
            'Image cannot be %s on this target' %
            'deployed' if key == DEPLOY else 'launched')

    def watchJob(self, job):
        last_status = None
        last_length = 0
        out = self.handle.ui.outStream

        while job.job_state.name in ['Queued', 'Running']:
            status = job.status_text
            length = len(status)

            if status != last_status:
                if out.isatty():
                    timeStamp = time.ctime(time.time())
                    out.write('\r[%s] %s' % (timeStamp, status))
                    if length < last_length:
                        i = last_length - length
                        out.write(' ' * i + '\b' * i)
                    out.flush()
                else:
                    self.handle.ui.progress(status.replace('%', '%%'))
            last_length = length
            last_status = status
            time.sleep(1)
            job.refresh()

        if job.job_state.name == 'Failed':
            raise errors.RbuildError('Image launch/deploy failed')
