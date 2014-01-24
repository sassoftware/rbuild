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

import re
import json

from smartform.descriptor import ConfigurationDescriptor
from smartform.descriptor_errors import ConstraintsValidationError

from rbuild import errors
from rbuild import pluginapi


class RbuilderCallback(object):
    def __init__(self, ui, config=None):
        self.ui = ui
        self._config = config or {}

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

            choices = [(self._description(x.descriptions), x.key)
                       for x in field.type]

            if field.default:
                # Find description for default
                defaultDescr = [x[0] for x in choices
                                if x[1] == field.default[0]][0]
                defmsg = " [default %s] " % defaultDescr
                prompt = "Enter choice (blank for default): "
            else:
                prompt = "Enter choice: "

            self.ui.write("Pick %s%s:" % (fieldDescr, defmsg))
            for i, (choice, _) in enumerate(choices):
                self.ui.write("\t%-2d: %s" % (i + 1, choice))

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
                return choices[data - 1][1]

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
            if value.lower() in ["yes", "yup", "y", "true", "1"]:
                return True
            else:
                return False
        else:
            return value


class DescriptorConfig(pluginapi.Plugin):
    name = 'descriptor_config'
    descriptorClass = ConfigurationDescriptor
    callbackClass = RbuilderCallback
    # TODO: Make this thread-safe
    _config = None

    def _parseDescriptorData(self, ddata):
        self._config.update(dict((f.name, ddata.getField(f.name))
                                 for f in ddata._descriptor.getDataFields()))

    def _read(self, filename):
        with open(filename) as fh:
            return json.load(fh)

    def _write(self, filename, data, append=False):
        mode = 'a' if append else 'w'
        with open(filename, mode) as fh:
            json.dump(data, fh, sort_keys=True, indent=2)

    def clearConfig(self):
        self.initialize()

    def createDescriptorData(self, fromStream=None):
        descr = self.descriptorClass(fromStream=fromStream)
        cb = self.callbackClass(self.handle.ui, self._config)
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
