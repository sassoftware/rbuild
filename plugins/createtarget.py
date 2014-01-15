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


import re

from smartform import descriptor, descriptor_errors
import yaml

from rbuild import errors
from rbuild import pluginapi
from rbuild.facade.rbuilderfacade import RbuilderCallback
from rbuild.pluginapi import command


class CreateTargetCommand(command.BaseCommand):
    help = 'Create a target on a SAS App Engine'
    paramHelp = '<TYPE>'

    def addLocalParameters(self, argDef):
        argDef['list'] = ('-l', command.NO_PARAM, 'List available target types')
        argDef['from-file'] = ('-f', command.ONE_PARAM,
                               'Load target config from yaml file')

    def runCommand(self, handle, argSet, args):
        ui = handle.ui
        rb = handle.facade.rbuilder

        list_types = argSet.pop('list', False)
        config_file = argSet.pop('from-file', None)

        if list_types:
            ui.write(
                "Available target types: %s" %
                ', '.join(rb.getTargetTypes().keys())
                )
            return

        if config_file:
            with open(config_file) as fh:
                config = yaml.safe_load(fh)
        else:
            config = None

        _, target_type = self.requireParameters(args, expected=['TYPE'])

        descriptor_xml = rb.getTargetDescriptor(target_type)
        if descriptor_xml is None:
            raise errors.RbuildError('No such target type: %s' % target_type)
        descr = descriptor.ConfigurationDescriptor(fromStream=descriptor_xml)

        # TODO: retry fields that fail validation rather than exiting
        cb = RbuilderCallback(ui, config)
        try:
            ddata = descr.createDescriptorData(cb)
        except descriptor_errors.ConstraintsValidationError as e:
            raise errors.RbuildError('\n'.join(m for m in e[0]))

        target = rb.createTarget(ddata, target_type)
        rb.configureTarget(target, ddata)

        creds_descr = descriptor.ConfigurationDescriptor(
            fromStream=target.actions[1].descriptor)
        creds_ddata = creds_descr.createDescriptorData(cb)
        rb.configureTargetCredentials(target, creds_ddata)


class CreateTarget(pluginapi.Plugin):
    name = 'target'

    def initialize(self):
        self.handle.Commands.getCommandClass('create').registerSubCommand(
            'target', CreateTargetCommand)
