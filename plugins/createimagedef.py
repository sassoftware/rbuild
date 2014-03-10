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


import itertools

from xobj import xobj

from rbuild import errors
from rbuild import pluginapi
from rbuild.pluginapi import command


DESCRIPTOR_PREFIX = 'options.'

DEFERRED = 'deferredImage'
ISO = 'applianceIsoImage'
AMI = 'amiImage'
XEN_OVA = 'xenOvaImage'
RAW_FS_IMAGE = 'rawFsImage'
RAW_HD_IMAGE = 'rawHdImage'
IMAGELESS = 'imageless'
TARBALL = 'tarballImage'
VMWARE_ESX = 'vmwareEsxImage'
VMWARE = 'vmwareImage'

IMAGEDEF_SPECS = {
    'iso': ISO,
    'ec2': AMI,
    'xen': XEN_OVA,
    'eucalyptus': RAW_FS_IMAGE,
    'kvm': RAW_HD_IMAGE,
    'parallels': RAW_HD_IMAGE,
    'qemu': RAW_HD_IMAGE,
    'raw_hd': RAW_HD_IMAGE,
    'layered': DEFERRED,
    'online_update': IMAGELESS,
    'tar': TARBALL,
    'cd': ISO,
    'dvd': ISO,
    'esx': VMWARE_ESX,
    'vcd': VMWARE_ESX,
    'vmware': VMWARE,
    'fusion': VMWARE,
}

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

        message = argSet.pop('message', None)
        listTypes = argSet.pop('list', False)
        fromFile = argSet.pop('from-file', None)
        toFile = argSet.pop('to-file', None)

        if listTypes:
            ui.write('Available image definition types: %s' %
                     ', '.join(IMAGEDEF_SPECS))
            return

        if fromFile:
            handle.DescriptorConfig.readConfig(fromFile)

        _, selectedType, arch = self.requireParameters(
            args, expected=['TYPE', 'ARCH'])
        imageType = IMAGEDEF_SPECS.get(selectedType)

        if not imageType:
            raise errors.PluginError(
                "No such image type '%s'. Valid image types are: %s" %
                (selectedType, ', '.join(sorted(IMAGEDEF_SPECS))))

        if arch not in ['x86', 'x86_64']:
            raise errors.PluginError(
                "No such architecture '%s'. Valid architectures are: x86 and"
                " x86_64" % arch)

        handle.CreateImageDef.create(imageType, arch, message)

        if toFile:
            handle.DescriptorConfig.writeConfig(toFile)


class CreateImageDef(pluginapi.Plugin):
    name = 'imagedef'

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

    def initialize(self):
        self.handle.Commands.getCommandClass('create').registerSubCommand(
            'imagedef', CreateImageDefCommand)

    def create(self, imageType, arch, message):
        '''
            Create an image definition

            @param imageType: type of image defintion to create
            @type imageType: str
            @return: image defintion
            @rtype: rObj(...)
        '''
        dc = self.handle.DescriptorConfig
        rb = self.handle.facade.rbuilder
        pd = self.handle.product
        ps = self.handle.productStore

        imageTypeDef = rb.getImageTypeDef(imageType, arch)
        containerRef = imageTypeDef.container.name
        flavorSetRef = imageTypeDef.flavorSet.name
        architectureRef = imageTypeDef.architecture.name

        self._checkBuildDef(containerRef, architectureRef, flavorSetRef)

        descriptor = xobj.toxml(imageTypeDef.descriptor._root)
        ddata = dc.createDescriptorData(fromStream=descriptor)

        imageFields = {}
        for field in imageTypeDef.options._xobj.attributes:
            imageFields[field] = getattr(imageTypeDef.options, field)

        for field in ddata.getFields():
            name = field.getName()
            if name.startswith(DESCRIPTOR_PREFIX):
                name = name.replace(DESCRIPTOR_PREFIX, '')
                if name == 'allowSnapshots':
                    # hack because options don't match
                    name = 'vmSnapshots'
                imageFields[name] = field.getValue()

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
