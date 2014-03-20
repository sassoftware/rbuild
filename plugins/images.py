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
delete images
'''
from rbuild import errors
from rbuild import pluginapi
from rbuild.pluginapi import command


class DeleteImagesCommand(command.BaseCommand):
    help = 'Delete images'
    paramHelp = '<job id>+'

    def runCommand(self, handle, argSet, args):
        handle.Build.checkProductStore()
        _, imageIds = self.requireParameters(
            args, expected=['IMAGEID'], appendExtra=True)
        for imageId in imageIds:
            handle.Images.delete(imageId)


class Images(pluginapi.Plugin):
    name = 'images'

    def initialize(self):
        self.handle.Commands.getCommandClass('delete').registerSubCommand(
            'images', DeleteImagesCommand)

    def delete(self, imageId):
        kwargs = {
            'image_id': imageId,
            'project': self.handle.product.getProductShortname(),
            }

        try:
            kwargs['stage'] = self.handle.productStore.getActiveStageName()
            kwargs['branch'] = self.handle.product.getBaseLabel()
        except errors.RbuildError:
            pass

        images = self.handle.facade.rbuilder.getImages(**kwargs)
        if images:
            images[0].delete()
        else:
            self.handle.ui.write("No image found with id '%s'" % imageId)
