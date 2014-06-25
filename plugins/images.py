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


'''
images
'''
import time

from xobj import xobj

from rbuild import errors
from rbuild import pluginapi
from rbuild.pluginapi import command


class DeleteImagesCommand(command.BaseCommand):
    help = 'Delete images'
    paramHelp = '<image id>+'

    def runCommand(self, handle, argSet, args):
        _, imageIds = self.requireParameters(
            args, expected=['IMAGEID'], appendExtra=True)
        for imageId in imageIds:
            try:
                imageId = int(imageId)
                handle.Images.delete(imageId)
            except ValueError:
                handle.ui.warning("Cannot parse image id '%s'" % imageId)


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
            job = handle.Images.deployImage(image, target, doLaunch)
        else:
            job = handle.Images.launchImage(image, target, doLaunch)

        if watch and doLaunch:
            handle.Images.watchJob(job)

        if toFile:
            handle.DescriptorConfig.writeConfig(toFile)


class ListImagesCommand(command.ListCommand):
    help = 'list images'
    resource = 'images'
    listFields = ('image_id', 'name', 'image_type', 'architecture', 'status',
        'status_message')
    listFieldMap = dict(
        image_type=dict(accessor=lambda i: i.image_type.name),
        )
    showFieldMap = dict(
        actions=dict(hidden=True),
        build_log=dict(accessor=lambda i: i._root.build_log.id),
        created_by=dict(accessor=lambda i: i.created_by.full_name),
        files=dict(
            accessor=lambda i: ', '.join('%s: %s' % (f.title, f.url)
                                         for f in i.files),
            ),
        jobs=dict(accessor=lambda i: i._root.jobs.id),
        project=dict(accessor=lambda i: i.project.name),
        project_branch=dict(accessor=lambda i: i.project_branch.name[0]),
        # add in fields definied in listFieldMap
        **listFieldMap
        )

    def _list(self, handle, *args, **kwargs):
        resources = super(ListImagesCommand, self)._list(
            handle, *args, **kwargs)
        if resources:
            handle.ui.write('\nLatest:')
            for latest in resources._node.latest_files:
                handle.ui.write(latest.id.replace('%', '%%'))
        return resources


class Images(pluginapi.Plugin):
    name = 'images'
    DEPLOY = 'deploy_image_on_target'
    LAUNCH = 'launch_system_on_target'

    def _createJob(self, action_type, image_name, target_name, doLaunch):
        rb = self.handle.facade.rbuilder

        project, branch, stage = self._getProductStage()
        image_name, _, version = image_name.partition('=')
        query_params = dict(
            project=project,
            branch=branch,
            stage=stage,
            order_by='-time_created',
            )
        if image_name.isdigit():
            query_params['image_id'] = image_name
        else:
            query_params['name'] = image_name

        if version:
            query_params['trailing_version'] = version
        images = rb.getImages(**query_params)
        if not images:
            raise errors.PluginError("No image matching '%s'" % image_name)

        target = rb.getTargets(name=target_name)
        if not target:
            raise errors.PluginError("No target matching '%s'" % target_name)
        target = target[0]
        if target.is_configured == 'false':
            raise errors.PluginError(("Target '{0}' is not configured. Try"
                " running \"rbuild edit target '{0}'\" or contacting"
                " your rbuilder administrator.").format(target.name))

        if target.credentials_valid == 'false':
            raise errors.PluginError(("Target '{0}' does not have valid"
                " credentials. Try running \"rbuild edit target '{0}'\""
                " and updating your credentials.").format(target.name))

        image, action = self._getAction(images, target, action_type)

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
                if key == action.key and target.name in action.name:
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

    def delete(self, imageId):
        self.handle.Build.checkStage()

        images = self.handle.facade.rbuilder.getImages(
            image_id=imageId,
            project=self.handle.product.getProductShortname(),
            branch=self.handle.product.getBaseLabel(),
            stage=self.handle.productStore.getActiveStageName(),
            )
        if images:
            images[0].delete()
        else:
            self.handle.ui.write("No image found with id '%s'" % imageId)

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

    def list(self):
        self.handle.Build.checkStage()
        images = self.handle.facade.rbuilder.getImages(
            project=self.handle.product.getProductShortname(),
            stage=self.handle.productStore.getActiveStageName(),
            branch=self.handle.product.getBaseLabel(),
            )
        return images

    def initialize(self):
        self.handle.Commands.getCommandClass('delete').registerSubCommand(
            'images', DeleteImagesCommand)
        self.handle.Commands.getCommandClass('list').registerSubCommand(
            'images', ListImagesCommand)

    def registerCommands(self):
        self.handle.Commands.registerCommand(LaunchCommand)

    def show(self, imageId):
        '''
            Show details of a specific image

            @param imageId: id of image
            @type imageId: str or int
        '''
        self.handle.Build.checkStage()
        image = self.handle.facade.rbuilder.getImages(
            image_id=imageId,
            project=self.handle.product.getProductShortname(),
            branch=self.handle.product.getBaseLabel(),
            stage=self.handle.productStore.getActiveStageName(),
            )
        if image:
            return image[0]

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
