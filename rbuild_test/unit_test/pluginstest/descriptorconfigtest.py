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
Test DescriptorConfig Plugin
'''

from rbuild import errors
from smartform.descriptor_errors import ConstraintsValidationError
from testutils import mock

from rbuild_test import rbuildhelp


class DescriptorConfigTest(rbuildhelp.RbuildHelper):
    def testCreateDescriptorData(self):
        handle = self.getRbuildHandle(mock.MockObject())
        dc = handle.DescriptorConfig
        dc.initialize()

        mock.mock(dc, 'callbackClass')
        mock.mock(dc, 'descriptorClass')
        mock.mockMethod(dc._parseDescriptorData)

        _ddata = mock.MockObject()
        _descr = mock.MockObject()
        _descr.createDescriptorData._mock.setReturn(
            _ddata, dc.callbackClass())
        dc.descriptorClass._mock.setReturn(_descr, fromStream='bar')

        self.assertEqual(
            dc.createDescriptorData(fromStream='bar'), _ddata)
        dc.callbackClass._mock.assertCalled(handle.ui, {}, None)
        dc._parseDescriptorData._mock.assertCalled(_ddata)

        dc._config = {'foo': 'FOO'}
        dc.createDescriptorData(fromStream='bar'),
        dc.callbackClass._mock.assertCalled(handle.ui, {'foo': 'FOO'}, None)
        dc._parseDescriptorData._mock.assertCalled(_ddata)

        _descr.createDescriptorData._mock.raiseErrorOnAccess(
            ConstraintsValidationError(['m1', 'm2']))
        err = self.assertRaises(
            errors.PluginError,
            dc.createDescriptorData,
            fromStream='bar')
        self.assertEqual(str(err), 'm1\nm2')
        dc._parseDescriptorData._mock.assertNotCalled()

    def testUpdateConfig(self):
        handle = self.getRbuildHandle(mock.MockObject())
        dc = handle.DescriptorConfig
        dc.initialize()
        dc._config = {
            'foo': 'FOO',
            'bar': 'BAR',
            }

        mock.mockMethod(dc._write)
        mock.mockMethod(dc._read, {'baz': 'BAZ'})
        dc.updateConfig('file.json')
        dc._write._mock.assertCalled('file.json', {
            'foo': 'FOO',
            'bar': 'BAR',
            'baz': 'BAZ',
            })

        dc._read._mock.setDefaultReturn({'baz': 'BAZ', 'bar': 'None'})
        dc.updateConfig('file.json')
        dc._write._mock.assertCalled('file.json', {
            'foo': 'FOO',
            'bar': 'BAR',
            'baz': 'BAZ',
            })

        dc.updateConfig('file.json', refresh=True)
        dc._write._mock.assertCalled('file.json', {
            'foo': 'FOO',
            'bar': 'BAR',
            'baz': 'BAZ',
            })
        self.assertEqual(
            dc._config, {'foo': 'FOO', 'bar': 'BAR', 'baz': 'BAZ'})

    def testParseDescriptorData(self):
        handle = self.getRbuildHandle(mock.MockObject())
        dc = handle.DescriptorConfig
        dc.initialize()

        _field1 = mock.MockObject()
        _field1._mock.set(name='foo', listType=None)

        _field2 = mock.MockObject()
        _field2._mock.set(name='bar', listType=None)

        _field3 = mock.MockObject()
        _field3._mock.set(name='baz', listType=True)

        _subf1 = mock.MockObject()
        _subf1.getName._mock.setReturn('name')
        _subf1.getValue._mock.setReturn('spam')

        _subf2 = mock.MockObject()
        _subf2.getName._mock.setReturn('value')
        _subf2.getValue._mock.setReturn('eggs')

        _subv1 = mock.MockObject()
        _subv1.getFields._mock.setReturn([_subf1, _subf2])

        _subv2 = {'afield': 'avalue', 'bfield': 'bvalue'}

        _ddata = mock.MockObject()
        _ddata.getField._mock.setReturn('FOO', 'foo')
        _ddata.getField._mock.setReturn('BAR', 'bar')
        _ddata.getField._mock.setReturn([_subv1, _subv2], 'baz')
        _ddata._descriptor.getDataFields._mock.setReturn([_field1, _field2])

        dc._parseDescriptorData(_ddata)
        self.assertEqual(dc._config, {'foo': 'FOO', 'bar': 'BAR'})

        _ddata._descriptor.getDataFields._mock.setReturn([_field3])

        dc._parseDescriptorData(_ddata)
        self.assertEqual(dc._config, {
            'foo': 'FOO',
            'bar': 'BAR',
            'baz': [
                {'name': 'spam', 'value': 'eggs'},
                {'afield': 'avalue', 'bfield': 'bvalue'},
                ],
            })

    def test_read(self):
        handle = self.getRbuildHandle(mock.MockObject())
        dc = handle.DescriptorConfig
        dc.initialize()

        filename = self.workDir + '/config.json'

        with open(filename, 'w') as fh:
            fh.write('''\
{
    "foo": "bar"
}
''')
        rv = dc._read(filename)
        self.assertEqual({"foo": "bar"}, rv)

        with open(filename, 'w') as fh:
            fh.write('''\
{
    "foo": "bar",
    "baz": spam
}
''')
        err = self.assertRaises(
            errors.ConfigParseError, dc._read, filename)
        self.assertEqual(
            "Error parsing '%s' at line 3 column 12 (char 31)" % filename,
            str(err),
            )
