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
from rbuild import errors
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
    fieldMap = (('ID', lambda i: i.image_id),
                ('Name', lambda i: i.name),
                ('Type', lambda i: i.image_type.name),
                ('Status', lambda i: i.status),
                ('Status Message', lambda i: (
                    i.status_message
                    if len(i.status_message) < 30
                    else i.status_message[:27] + '...')),
                )


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
        return self.handle.facade.rbuilder.getImages(
            project=self.handle.product.getProductShortname(),
            stage=self.handle.productStore.getActiveStageName(),
            branch=self.handle.product.getBaseLabel(),
            )
