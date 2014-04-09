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
image definitions
'''
from rbuild import pluginapi
from rbuild.pluginapi import command

import epdb

class ListImageDefsCommand(command.ListCommand):
    help = 'list image definitions'
    resource = 'imagedefs'
    listFields = ('id', 'name', 'container', 'architecture')
    listFieldMap = dict(
        id=dict(accessor=lambda i: i.id.rsplit('/')[-1]),
        container=dict(
            display_name='Type',
            accessor=lambda i: i.container.displayName,
            ),
        architecture=dict(
            accessor=lambda i: i.architecture.displayName,
            ),
        )
    showFieldMap = dict(
        descriptor=dict(hidden=True),
        flavorSet=dict(
            display_name="Flavor Set",
            accessor=lambda i: i.flavorSet.displayName,
            ),
        options=dict(
            display_name="Options",
            accessor=lambda i: ''.join(
                '\n  %s: %s' % (k, getattr(i.options, k))
                for k in i.options._xobj.attributes.keys()
                if getattr(i.options, k)),
            ),
        stage=dict(
            display_name='Stages',
            accessor=lambda i: ', '.join(
                stage.href.rsplit('/', 1)[-1] for stage in i.stage),
            ),
        **listFieldMap
        )


class ImageDefs(pluginapi.Plugin):
    name = 'imagedefs'

    def initialize(self):
        self.handle.Commands.getCommandClass('list').registerSubCommand(
            'imagedefs', ListImageDefsCommand)

    def list(self):
        self.handle.Build.checkProductStore()
        return self.handle.facade.rbuilder.getImageDefs(
            product=self.handle.product.getProductShortname(),
            version=self.handle.product.getProductVersion(),
            )

    def show(self, imageDefId):
        self.handle.Build.checkProductStore()
        imageDef = self.handle.facade.rbuilder.getImageDefs(
            id=imageDefId,
            product=self.handle.product.getProductShortname(),
            version=self.handle.product.getProductVersion(),
            )
        if imageDef:
            return imageDef[0]
