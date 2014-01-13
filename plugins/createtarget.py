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
        try:
            ddata = descr.createDescriptorData(Callback(ui, config))
        except descriptor_errors.ConstraintsValidationError as e:
            raise errors.RbuildError('\n'.join(m for m in e[0]))

        target = rb.createTarget(ddata, target_type)
        rb.configureTarget(target, ddata)

        creds_descr = descriptor.ConfigurationDescriptor(
            fromStream=target.actions[1].descriptor)
        creds_ddata = creds_descr.createDescriptorData(Callback(ui, config))
        rb.configureTargetCredentials(target, creds_ddata)


class CreateTargetPlugin(pluginapi.Plugin):
    name = 'target'

    def initialize(self):
        self.handle.Commands.getCommandClass('create').registerSubCommand(
            'target', CreateTargetCommand)


class Callback(object):
    def __init__(self, ui, config):
        self.ui = ui
        self.config = config or {}

    def start(self, descriptor, name=None):
        pass

    def end(self, descriptor):
        pass

    def getValueForField(self, field):
        # prefer pre-configured values if they are available
        if field.name in self.config:
            return self.config[field.name]

        val = self._getValueForField(field)
        return val

    def _description(cls, description):
        """
        Normally descriptions should always have a "default" empty lang, but
        sometimes we set en_US. So try to fetch None first, and if that fails,
        get the first value and hope for the best.
        """
        descriptions = description.asDict()
        return descriptions.get(None, descriptions.values()[0])


    def _getValueForField(self, field):
        ''' helper function that returns the value for the field, but does not store
    it '''

        defmsg = "" # message about the default value, if there is one
        reqmsg = "" # message about whether the field is required, if so
        typmsg = " (type %s)" % field.type

        if field.required and field.hidden and field.default:
            # return the default value and don't ask the user for input
            if field.multiple:
                return field.default
            return field.default[0]

        if field.required:
            # tell the user this is a required field
            reqmsg = " [required]"

        # get the description for the field
        fieldDescr = self._description(field.get_descriptions())

        if field.enumeratedType:
            # FIXME: refactor into subfunction

            # print a list of options and let the user choose it by number

            choices = [ (self._description(x.descriptions), x.key)
                    for x in field.type ]

            if field.default:
                # Find description for default
                defaultDescr = [ x[0] for x in choices
                        if x[1] == field.default[0] ][0]
                defmsg = " [default %s] " % defaultDescr
                prompt = "Enter choice (blank for default): "
            else:
                prompt = "Enter choice: "

            self.ui.write("Pick %s%s:" % (fieldDescr, defmsg))
            for i, (choice, _) in enumerate(choices):
                self.ui.write("\t%-2d: %s" % (i+1, choice))

            # enumerated type input
            # loop while the user hasn't entered a valid number
            while 1:

                data = self.ui.input(prompt).strip()

                # FIXME: error checking
                if not data:
                    # user entered blank input
                    # if no default is present, prompt again
                    if not field.default:
                        continue
                    data = 0
                else:
                    # ensure user entered an integer
                    try:
                        data = int(data)
                    except ValueError:
                        continue

                # make sure the user input is inside the valid range
                rangeMax = len(choices)
                rangeMin = 0 if field.default else 1
                if not (rangeMin <= data <= rangeMax):
                    continue

                # if selected the 0th element, return the default
                if data == 0:
                    return field.default[0]
                # return the selected choice
                return choices[data-1][1]

        # for non enumerated types ...

        # if there is a default, say what it is
        if field.default:
            defmsg = " [default %s]" % str(field.default[0])

        # FIXME: refactor into subfunction
        # TODO: nicer entry on the same line, try on certain failures in casting, etc
        prompt = "Enter %s%s%s%s: " % (fieldDescr, reqmsg, defmsg, typmsg)
        while 1:
            if re.search(r'[Pp]assword', prompt):
                data = self.ui.inputPassword(prompt)
            else:
                data = self.ui.input(prompt).strip()
            if data == '':
                # if input is blank use the entered default data if it exists
                if field.default:
                    data = field.default[0]
                elif field.required:
                    # if blank and required, input again
                    continue
                else:
                    # Assume the user chose not to fill in the value
                    return None
            try:
                # convert true/yes/etc to booleans and so on
                return self.cast(data, field.type)
            except ValueError:
                continue

    def cast(self, value, typename):
        # FIXME: we can probably do a getattr on the core namespace here
        if typename == 'str':
            return value
        elif typename == 'int':
            return int(value)
        elif typename == 'float':
            return float(value)
        elif typename == 'bool':
            if value.lower() in [ "yes", "yup", "y", "true", "1" ]:
                return True
            else:
                return False
        else:
            return value
