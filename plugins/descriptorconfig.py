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
Plugin for reading and writing descriptor config files
"""

import json
import os
import re

from smartform.descriptor import ConfigurationDescriptor
from smartform.descriptor_errors import ConstraintsValidationError

from rbuild import errors
from rbuild import pluginapi


class RbuilderCallback(object):
    def __init__(self, ui, config=None, defaults=None):
        self.ui = ui
        self._config = config or {}
        self._defaults = defaults or {}

    def _enumeratedType(self, field):
        prompt = "Enter choice"
        choices = [self._description(x.descriptions) for x in field.type]
        default = [idx for idx, x in enumerate(field.type)
                   if x.key in field.default]
        if default:
            prompt += " (blank for default)"

        if field.multiple:
            response = self.ui.getChoices(prompt, choices,
                default=default if default else None)
            return [field.type[r].key for r in response]
        else:
            response = self.ui.getChoice(prompt, choices,
                default=default[0] if default else None)
            return field.type[response].key

    def _listType(self, field):
        responses = []
        self.ui.write('Enter %s (type Ctrl-D to end input)' % field.name)
        while True:
            try:
                response = field._descriptor.createDescriptorData(
                    self, name=field.name)
            except errors.RbuildError as e:
                if 'Ran out of input' in str(e):
                    return responses
                raise
            responses.append(response)

    def start(self, descriptor, name=None):
        pass

    def end(self, descriptor):
        pass

    def getValueForField(self, field):
        # prefer pre-configured values if they are available
        if field.name in self._config:
            val = self._config[field.name]
        else:
            val = self._getValueForField(field)
        return val

    def _description(cls, description):
        """
            Normally descriptions should always have a "default" empty lang,
            but sometimes we set en_US. So try to fetch None first, and if that
            fails, get the first value and hope for the best.
        """
        descriptions = description.asDict()
        return descriptions.get(None, descriptions.values()[0])

    def _getValueForField(self, field):
        '''
            helper function that returns the value for the field, but does not
            store it
        '''

        defmsg = ""  # message about the default value, if there is one
        reqmsg = ""  # message about whether the field is required, if so

        if field.listType:
            typmsg = " (type list)"
        else:
            typmsg = " (type %s)" % field.type

        if field.name in self._defaults:
            # override the field's default value with ours
            if field.multiple:
                defaults = []
                for value in self._defaults[field.name]:
                    default = self.reverse_cast(value, field.type)
                    if default:
                        defaults.append(default)
                field.default = defaults
            else:
                default = self.reverse_cast(
                    self._defaults[field.name], field.type)
                field.default = [default] if default else []

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
            return self._enumeratedType(field)

        if field.listType:
            return self._listType(field)

        # for non enumerated types ...
        # if there is a default, say what it is
        if field.default:
            defmsg = " [default %s]" % str(field.default[0])

        # FIXME: refactor into subfunction
        # TODO: nicer entry on the same line, try on certain failures
        #       in casting, etc
        prompt = "Enter %s%s%s%s: " % (fieldDescr, reqmsg, defmsg, typmsg)
        while 1:
            if re.search(r'[Pp]assword', prompt):
                data = self.ui.inputPassword(prompt)
            else:
                data = self.ui.getResponse(
                    prompt,
                    default=field.default[0] if field.default else None,
                    required=field.required,
                    )
            if data == '':
                # the user chose not to fill in the value
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
            if value.lower() in ["yes", "yup", "y", "true", "1"]:
                return True
            else:
                return False
        else:
            return value

    def reverse_cast(self, value, typename):
        if typename == 'bool':
            if value is True:
                return 'yes'
            else:
                return 'no'
        else:
            return str(value)


class DescriptorConfig(pluginapi.Plugin):
    name = 'descriptor_config'
    descriptorClass = ConfigurationDescriptor
    callbackClass = RbuilderCallback
    # TODO: Make this thread-safe
    _config = None

    def _parseDescriptorData(self, ddata):
        config = dict()
        for dataField in ddata._descriptor.getDataFields():
            # TODO: need to handle nested compound fields here
            # for now we assume the list is shallow
            value = ddata.getField(dataField.name)
            if dataField.listType:
                _value = []
                for subv in value:
                    if hasattr(subv, 'getFields'):
                        _value.append(dict((f.getName(), f.getValue())
                                           for f in subv.getFields()))
                    else:
                        _value.append(subv)
                value = _value
            config[dataField.name] = value
        self._config.update(config)

    def _read(self, filename):
        with open(os.path.expanduser(filename)) as fh:
            try:
                return json.load(fh)
            except ValueError as e:
                location = str(e).rpartition(':')[-1].strip()
                raise errors.ConfigParseError(file=filename, location=location)

    def _write(self, filename, data, append=False):
        mode = 'a' if append else 'w'
        with open(os.path.expanduser(filename), mode) as fh:
            json.dump(data, fh, sort_keys=True, indent=2)

    def clearConfig(self):
        self.initialize()

    def createDescriptorData(self, fromStream=None, defaults=None):
        descr = self.descriptorClass(fromStream=fromStream)
        cb = self.callbackClass(self.handle.ui, self._config, defaults)
        try:
            ddata = descr.createDescriptorData(cb)
        except ConstraintsValidationError as e:
            raise errors.PluginError('\n'.join(m for m in e[0]))
        self._parseDescriptorData(ddata)
        return ddata

    def initialize(self):
        self._config = {}

    def readConfig(self, filename):
        '''
            Read a config file

            @param filename: name of file
            @type filename: str
            @return: configuration
            @rtype: dict
        '''
        self._config = self._read(filename)

    def updateConfig(self, filename, refresh=False):
        '''
            Update an existing config file with this config. Does not store the
            combined configuration, unless refresh is True

            @param filename: name of file
            @type filename: str
            @param refresh: whether to refresh with the combined config
            @type refresh: bool
        '''
        try:
            file_config = self._read(filename)
        except IOError:
            file_config = {}
        file_config.update(self._config)
        self._write(filename, file_config)
        if refresh:
            self._config = file_config

    def writeConfig(self, filename):
        '''
            Write config to file

            @param filename: name of file
            @type filename: str
        '''
        self._write(filename, self._config)
