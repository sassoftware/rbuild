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
            'no-launch': 'Do not launch an image',
            }

    def addLocalParameters(self, argDef):
        argDef['list'] = '-l', command.NO_PARAM
        argDef['from-file'] = '-f', command.ONE_PARAM
        argDef['to-file'] = '-o', command.ONE_PARAM
        argDef['no-watch'] = command.NO_PARAM
        argDef['no-launch'] = command.NO_PARAM

    def runCommand(self, handle, argSet, args):
        ui = handle.ui
        rb = handle.facade.rbuilder

        listTargets = argSet.pop('list', False)
        fromFile = argSet.pop('from-file', None)
        toFile = argSet.pop('to-file', None)
        watch = not argSet.pop('no-watch', False)
        doLaunch = not argSet.pop('no-launch', False)

        if listTargets:
            ui.write('Available targets: %s' %
                     ', '.join(t.name for t in rb.getEnabledTargets()))
            return

        if fromFile:
            handle.DescriptorConfig.readConfig(fromFile)

        command, image, target = self.requireParameters(
            args, expected=['IMAGE', 'TARGET'])

        if command == 'deploy':
            job = handle.Launch.deployImage(image, target, doLaunch)
        else:
            job = handle.Launch.launchImage(image, target, doLaunch)

        if watch and doLaunch:
            handle.Launch.watchJob(job)

        if toFile:
            handle.DescriptorConfig.writeConfig(toFile)


class Launch(pluginapi.Plugin):
    name = 'launch'
    DEPLOY = 'deploy_image_on_target'
    LAUNCH = 'launch_system_on_target'

    def _createJob(self, action_type, image_name, target_name, doLaunch):
        rb = self.handle.facade.rbuilder

        project, branch, stage = self._getProductStage()
        image_name, _, version = image_name.partition('=')
        images = rb.getImages(
            image_name,
            project=project,
            branch=branch,
            stage=stage,
            trailingVersion=version,
            )

        image, action = self._getAction(images, target_name, action_type)

        ddata = self.handle.DescriptorConfig.createDescriptorData(
            fromStream=action.descriptor)

        doc = xobj.Document()
        doc.job = job = xobj.XObj()

        job.job_type = action._root.job_type
        job.descriptor = action._root.descriptor
        job.descriptor_data = xobj.parse(ddata.toxml()).descriptor_data

        if doLaunch:
            return image.jobs.append(doc)

    def _getAction(self, images, target, key):
        assert key in (self.DEPLOY, self.LAUNCH)

        for image in images:
            if image.status != '300':
                continue
            for action in image.actions:
                if key == action.key and target in action.name:
                    return image, action
        raise errors.PluginError(
            "cannot %s %s" % (key.replace('_', ' '), target))

    def _getProductStage(self):
        try:
            product = self.handle.product.getProductShortname()
            baseLabel = self.handle.product.getBaseLabel()
        except AttributeError:
            raise errors.PluginError(
                'Current directory is not part of a product.\n'
                'To initialize a new product directory, use "rbuild init"')

        try:
            stage = self.handle.productStore.getActiveStageName()
        except errors.RbuildError:
            raise errors.PluginError(
                'Current directory is not a product stage.')
        return (product, baseLabel, stage)

    def registerCommands(self):
        self.handle.Commands.registerCommand(LaunchCommand)

    def deployImage(self, *args, **kwargs):
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
        return self._createJob(self.DEPLOY, *args, **kwargs)

    def launchImage(self, *args, **kwargs):
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
        return self._createJob(self.LAUNCH, *args, **kwargs)

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
