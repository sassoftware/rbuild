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
from rbuild import pluginapi
from rbuild.pluginapi import command


class DeleteImagesCommand(command.BaseCommand):
    help = 'Delete images'
    paramHelp = '<job id>+'

    def runCommand(self, handle, argSet, args):
        _, imageIds = self.requireParameters(
            args, expected=['IMAGEID'], appendExtra=True)
        for imageId in imageIds:
            handle.Images.delete(imageId)


class ListImagesCommand(command.ListCommand):
    help = 'list images'
    resource = 'images'
    listFields = ('image_id', 'name', 'image_type', 'status', 'status_message')
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
                handle.ui.write(latest.id)
        return resources


class Images(pluginapi.Plugin):
    name = 'images'

    def initialize(self):
        self.handle.Commands.getCommandClass('delete').registerSubCommand(
            'images', DeleteImagesCommand)
        self.handle.Commands.getCommandClass('list').registerSubCommand(
            'images', ListImagesCommand)

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

    def list(self):
        self.handle.Build.checkStage()
        images = self.handle.facade.rbuilder.getImages(
            project=self.handle.product.getProductShortname(),
            stage=self.handle.productStore.getActiveStageName(),
            branch=self.handle.product.getBaseLabel(),
            )
        return images

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
