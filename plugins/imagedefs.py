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
import itertools

from xobj import xobj

from rbuild import errors
from rbuild import pluginapi
from rbuild.productstore.decorators import requiresProduct
from rbuild.pluginapi import command


DESCRIPTOR_PREFIX = 'options.'


class CreateImageDefCommand(command.BaseCommand):
    help = 'Create a image defintion on a SAS App Engine'
    commands = ['imagedef']
    paramHelp = '<TYPE> <ARCH>'
    docs = {'list': 'List available image types',
            'from-file': 'Load config from file',
            'to-file': 'Write config to file',
            }

    def addLocalParameters(self, argDef):
        argDef['message'] = '-m', command.ONE_PARAM
        argDef['list'] = '-l', command.NO_PARAM
        argDef['from-file'] = '-f', command.ONE_PARAM
        argDef['to-file'] = '-o', command.ONE_PARAM

    def runCommand(self, handle, argSet, args):
        ui = handle.ui
        rb = handle.facade.rbuilder

        message = argSet.pop('message', None)
        listTypes = argSet.pop('list', False)
        fromFile = argSet.pop('from-file', None)
        toFile = argSet.pop('to-file', None)

        if fromFile:
            handle.DescriptorConfig.readConfig(fromFile)

        _, type, arch = self.requireParameters(
            args, expected=['TYPE', 'ARCH'])

        imageType = [i for i in rb.getImageTypes() if i.name == type]
        if not imageType:
            raise errors.PluginError("No such image type '%s'."
                " Run `rbuild list imagetypes` to see valid image types" % type)
        imageType = imageType[0]

        if arch not in ['x86', 'x86_64']:
            raise errors.PluginError(
                "No such architecture '%s'. Valid architectures are: x86 and"
                " x86_64" % arch)

        handle.ImageDefs.create(imageType, arch, message)

        if toFile:
            handle.DescriptorConfig.writeConfig(toFile)


class ListImageDefsCommand(command.ListCommand):
    help = 'list image definitions'
    resource = 'imagedefs'
    listFields = ('id', 'name', 'container', 'architecture')

    def _generateTypeDisplayName(i):
        try:
            if i.options.ebsBacked == 'true':
                extra = " (EBS)"
            else:
                extra = ""
        except AttributeError:  # no 'ebsBacked' attribute for non-AMI images
            extra = ""

        return i.container.displayName + extra

    listFieldMap = dict(
        id=dict(accessor=lambda i: i.id.rsplit('/')[-1]),
        container=dict(
            display_name='Type',
            accessor=_generateTypeDisplayName,
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
            accessor=lambda i: ', '.join(stage.href.rsplit('/')[-1] for stage in i.stage)
                if isinstance(i.stage, list) else i.stage.name,
            ),
        **listFieldMap
        )


class ImageDefs(pluginapi.Plugin):
    name = 'imagedefs'

    def _checkBuildDef(self, *args):
        assert len(args) == 3
        prodDef = self.handle.product

        if prodDef.platform:
            templateIter = itertools.chain(
                prodDef.getBuildTemplates(),
                prodDef.platform.getBuildTemplates(),
                )
        else:
            # It is valid for the platform to be missing (although not
            # terribly useful)
            templateIter = prodDef.getBuildTemplates()
        allowedCombinations = set(
            (bt.containerTemplateRef, bt.architectureRef, bt.flavorSetRef)
            for bt in templateIter)
        if args not in allowedCombinations:
            raise errors.PluginError(
                "Invalid combination of container template, architecture and "
                "flavor set (%s, %s, %s)" % args)
        return True

    def create(self, imageType, arch, message):
        '''
            Create an image definition

            @param imageType: type of image defintion to create
            @type imageType: rObj(image_type)
            @return: image defintion
            @rtype: rObj(...)
        '''
        dc = self.handle.DescriptorConfig
        rb = self.handle.facade.rbuilder
        pd = self.handle.product
        ps = self.handle.productStore

        descriptor = xobj.toxml(imageType.descriptor._root)
        ddata = dc.createDescriptorData(fromStream=descriptor)

        imageTypeDef = rb.getImageTypeDef(imageType.name, arch)
        containerRef = imageTypeDef.container.name
        flavorSetRef = imageTypeDef.flavorSet.name
        architectureRef = imageTypeDef.architecture.name

        self._checkBuildDef(containerRef, architectureRef, flavorSetRef)

        imageFields = {}
        for field in imageTypeDef.options._xobj.attributes:
            imageFields[field] = getattr(imageTypeDef.options, field)

        for field in ddata.getFields():
            name = field.getName()
            if name.startswith(DESCRIPTOR_PREFIX):
                name = name.replace(DESCRIPTOR_PREFIX, '')
                imageFields[name] = field.getValue()

        # FIXME: Map allowSnapshots -> vmSnapshots since the smartform and
        #        proddef differ. (RCE-2743)
        if 'allowSnapshots' in imageFields:
            imageFields['vmSnapshots'] = imageFields.pop('allowSnapshots')

        stages = [s.name for s in pd.getStages()]

        pd.addBuildDefinition(
            name=ddata.getField('displayName'),
            containerTemplateRef=containerRef,
            architectureRef=architectureRef,
            flavorSetRef=flavorSetRef,
            image=pd.imageType(None, imageFields),
            stages=stages,
            )
        with open(ps.getProductDefinitionXmlPath(), 'w') as fh:
            pd.serialize(fh, validate=True)

        if message is None:
            message = 'Add image def %s' % ddata.getField('displayName')
        ps.commit(message=message)
        ps.update()

    def initialize(self):
        self.handle.Commands.getCommandClass('create').registerSubCommand(
            'imagedef', CreateImageDefCommand)
        self.handle.Commands.getCommandClass('list').registerSubCommand(
            'imagedefs', ListImageDefsCommand)

    @requiresProduct
    def list(self):
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
