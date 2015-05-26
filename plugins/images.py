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
from datetime import datetime
import os
import time

from xobj import xobj

from rbuild import errors
from rbuild import pluginapi
from rbuild.lib import util
from rbuild.productstore.decorators import requiresStage
from rbuild.pluginapi import command


class CancelImageError(errors.RbuildError):
    """Raised when there is an error canceling an image build"""


class MissingImageError(errors.RbuildError):
    """Raised when we don"t find an image"""
    template = ("Unable to find image with id '%(image)s' on %(stage)s stage"
        " of %(project)s project")
    params = ["image", "project", "stage"]


class CancelImagesCommand(command.BaseCommand):
    help = 'Cancel image build'
    paramHelp = '<id>+'

    def runCommand(self, handle, argSet, args):
        _, imageIds = self.requireParameters(args, expected=['id'],
            appendExtra=True)

        project, branch, stage = handle.Images._getProductStage()
        for imageId in imageIds:
            try:
                int(imageId)
            except ValueError:
                raise errors.BadParameterError(
                    "Cannot parse image id '%s'" % imageId)

            image = handle.facade.rbuilder.getImages(image_id=imageId,
                project=project, branch=branch, stage=stage)

            if not image:
                handle.ui.warning(str(MissingImageError(image=imageId,
                    project=project, stage=stage)))
                continue
            image = image[0]

            try:
                handle.Images.cancel(image)
            except CancelImageError as err:
                handle.ui.warning(str(err))


class DeleteImagesCommand(command.BaseCommand):
    help = 'Delete images'
    paramHelp = '<image id>+'
    docs = {"force": "Delete images without prompting",
            }

    def addLocalParameters(self, argDef):
        argDef["force"] = "-f", command.NO_PARAM

    def runCommand(self, handle, argSet, args):
        force = argSet.pop("force", False)
        _, imageIds = self.requireParameters(
            args, expected=['IMAGEID'], appendExtra=True)
        for imageId in imageIds:
            try:
                int(imageId)
                handle.Images.delete(imageId, force)
            except ValueError:
                handle.ui.warning("Cannot parse image id '%s'" % imageId)


class LaunchCommand(command.BaseCommand):
    help = 'Launch/Deploy an image onto a target'
    paramHelp = '<image name[=version] | image id> <target name>'
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
            args, expected=['image name or id', 'target name'])

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
    listFields = ('image_id', 'name', 'image_type', 'architecture',
        'trailing_version', 'time_created', 'status', 'status_message',)
    listFieldMap = dict(
        image_type=dict(accessor=lambda i: i.image_type.name),
        trailing_version=dict(display_name='Version'),
        time_created=dict(display_name="Created",
                          accessor=lambda i: util.convertTime(i.time_created))
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
                try:
                    image_link = latest.id.replace('%', '%%')
                except AttributeError:
                    image_link = 'Latest images link not found'
                handle.ui.write(image_link)
        return resources


class Images(pluginapi.Plugin):
    name = 'images'
    DEPLOY = 'deploy_image_on_target'
    LAUNCH = 'launch_system_on_target'
    CANCEL = 'image_build_cancellation'

    def _createJob(self, action_type, image_name, target_name, doLaunch):
        rb = self.handle.facade.rbuilder

        project, branch, stage = self._getProductStage()
        query_params = dict(
            project=project,
            branch=branch,
            stage=stage,
            order_by='-time_created',
            )
        if image_name.isdigit():
            query_params['image_id'] = image_name
        else:
            image_name, _, version = image_name.partition('=')
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

    @requiresStage
    def _getProductStage(self):
        product = self.handle.product.getProductShortname()
        baseLabel = self.handle.product.getBaseLabel()
        stage = self.handle.productStore.getActiveStageName()
        return (product, baseLabel, stage)

    def cancel(self, image):
        '''
        Cancel a currently running image build

        :param image: image obj
        :type image: rObj(image)
        '''
        if image.status != '100':
            raise CancelImageError(msg="Image '%s' is not currently building" %
                image.image_id)

        cancelAction = [a for a in image.actions if a.key == self.CANCEL]
        if not cancelAction:
            raise CancelImageError(msg="Unable to find cancel action for"
                " image '%s'" % image.image_id)
        cancelAction = cancelAction[0]
        ddata = self.handle.DescriptorConfig.createDescriptorData(
            fromStream=cancelAction.descriptor)
        doc = xobj.Document()
        doc.job = job = xobj.XObj()

        job.job_type = cancelAction._root.job_type
        job.descriptor = cancelAction._root.descriptor
        job.descriptor_data = xobj.parse(ddata.toxml()).descriptor_data
        return image.jobs.append(doc)

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

    def delete(self, imageId, force=False):
        shortName, baseLabel, stageName = self._getProductStage()

        images = self.handle.facade.rbuilder.getImages(image_id=imageId,
            project=shortName, branch=baseLabel, stage=stageName)
        if images:
            if force or self.handle.ui.getYn(
                    "Delete {0}?".format(images[0].name),
                    default=False,
                    ):
                images[0].delete()
        else:
            raise MissingImageError(image=imageId, project=shortName,
                stage=stageName)

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
        shortName, baseLabel, stageName = self._getProductStage()
        images = self.handle.facade.rbuilder.getImages(project=shortName,
            stage=stageName, branch=baseLabel)
        return images

    def initialize(self):
        for command, subcommand, commandClass in (
                ('cancel', 'images', CancelImagesCommand),
                ('delete', 'images', DeleteImagesCommand),
                ('list', 'images', ListImagesCommand),
                ('show', 'images', ListImagesCommand),
                ):
            cmd = self.handle.Commands.getCommandClass(command)
            cmd.registerSubCommand(subcommand, commandClass)

    def registerCommands(self):
        self.handle.Commands.registerCommand(LaunchCommand)

    def show(self, imageId):
        '''
            Show details of a specific image

            @param imageId: id of image
            @type imageId: str or int
        '''
        shortName, baseLabel, stageName = self._getProductStage()
        image = self.handle.facade.rbuilder.getImages(image_id=imageId,
            project=shortName, branch=baseLabel, stage=stageName)
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
