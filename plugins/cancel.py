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
cancel command and related utilities.
"""

from operator import attrgetter
import itertools

from xobj import xobj

from rbuild import errors, pluginapi
from rbuild.pluginapi import command


class CancelCommand(command.CommandWithSubCommands):
    #pylint: disable-msg=R0923
    # "the creature can't help its ancestry"
    help = 'Cancels rbuild operations'

    commands = ['cancel']


class CancelImagesCommand(command.BaseCommand):
    help = 'Cancel image build'
    paramHelp = '[options] [NAME]*'

    def runCommand(self, handle, argSet, args):
        _, imageNames = self.requireParameters(args, allowExtra=True)
        handle.Cancel.cancelImages(imageNames)


class Cancel(pluginapi.Plugin):
    name = 'cancel'

    def _cancelImage(self, images):
        if not isinstance(images, list):
            images = [images]

        for image in images:
            if self._promptUser(image):
                job = self._getCancelBuildJob(image)
                if job and job.status_code != '200':
                    raise errors.PluginError(job.status_text)

    def _getBuildingImages(self, name=None):
        try:
            project = self.handle.product.getProductName()
            baseLabel = self.handle.product.getBaseLabel()
            parent = self.handle.facade.rbuilder.getProject(project)
        except AttributeError:
            return []

        try:
            stageName = self.handle.productStore.getActiveStageName()
        except errors.RbuildError:
            stageName = None

        if stageName:
            for branch in parent.project_branches:
                if branch.label == baseLabel:
                    break
            for stage in branch.project_branch_stages:
                if stage.name == stageName:
                    break
            parent = stage

        if parent.images:
            if name:
                imageFilter = lambda x: x.status == '100' and x.name == name
            else:
                imageFilter = lambda x: x.status == '100'
            return sorted(
                itertools.ifilter(imageFilter, parent.images),
                key=attrgetter('time_created'),
                reverse=True,
                )
        else:
            return []

    def _getCancelBuildJob(self, image):
            cancelAction = image.actions[0]
            ddata = self.handle.DescriptorConfig.createDescriptorData(
                fromStream=cancelAction.descriptor)
            doc = xobj.Document()
            doc.job = job = xobj.XObj()

            job.job_type = cancelAction._root.job_type
            job.descriptor = cancelAction._root.descriptor
            job.descriptor_data = xobj.parse(ddata.toxml()).descriptor_data
            return image.jobs.append(doc)

    def _promptUser(self, image):
        return self.handle.ui.getYn(
            "Cancel image build '%s=%s started on %s' [Y/n]" %
            (image.name, image.trailing_version, image.time_created))

    def initialize(self):
        cmd = self.handle.Commands.getCommandClass('cancel')
        cmd.registerSubCommand('images', CancelImagesCommand)

    def registerCommands(self):
        self.handle.Commands.registerCommand(CancelCommand)

    def cancelImage(self, name):
        images = self._getBuildingImages(name)
        if not images:
            self.handle.ui.write("No image with name '%s' found" % name)
        else:
            self._cancelImage(images)

    def cancelImages(self, names=None):
        if names:
            for name in names:
                self.cancelImage(name)
        else:
            images = self._getBuildingImages()
            if not images:
                self.handle.ui.write("No image are currently building")
            else:
                self._cancelImage(images)
