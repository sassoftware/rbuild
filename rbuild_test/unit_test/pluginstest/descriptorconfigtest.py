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
        _field1._mock.set(name='foo')

        _field2 = mock.MockObject()
        _field2._mock.set(name='bar')

        _field3 = mock.MockObject()
        _field3._mock.set(name='baz')

        _ddata = mock.MockObject()
        _ddata.getField._mock.setReturn('FOO', 'foo')
        _ddata.getField._mock.setReturn('BAR', 'bar')
        _ddata.getField._mock.setReturn('BAZ', 'baz')
        _ddata._descriptor.getDataFields._mock.setReturn([_field1, _field2])

        dc._parseDescriptorData(_ddata)
        self.assertEqual(dc._config, {'foo': 'FOO', 'bar': 'BAR'})

        _ddata._descriptor.getDataFields._mock.setReturn([_field3])

        dc._parseDescriptorData(_ddata)
        self.assertEqual(dc._config, {'foo': 'FOO', 'bar': 'BAR', 'baz': 'BAZ'})

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

    def testCallbackEnumerated(self):
        handle = self.getRbuildHandle(mock.MockObject())
        callback = handle.DescriptorConfig.callbackClass(handle.ui)
        fDef = handle.DescriptorConfig.descriptorClass()
        fDef.addDataField('lotsaValues',
            descriptions=[fDef.Description("foo")],
            type=fDef.EnumeratedType([
                fDef.ValueWithDescription('one',
                    descriptions=[fDef.Description("One")]),
                fDef.ValueWithDescription('two',
                    descriptions=[fDef.Description("Two")]),
            ]))
        fDef.addDataField('lotsaValuesDefault',
            descriptions=[fDef.Description("foo")],
            default=['two'],
            type=fDef.EnumeratedType([
                fDef.ValueWithDescription('one',
                    descriptions=[fDef.Description("One")]),
                fDef.ValueWithDescription('two',
                    descriptions=[fDef.Description("Two")]),
            ]))

        mock.mockMethod(handle.ui.getChoice)

        # field with no default
        handle.ui.getChoice._mock.setReturn(0,
            'Enter choice',
            ["One", "Two"], default=None)
        rv = callback.getValueForField(fDef.getDataField('lotsaValues'))
        self.assertEqual(rv, 'one')

        # field with default
        handle.ui.getChoice._mock.setReturn(0,
            'Enter choice (blank for default)',
            ["One", "Two"], default=1)
        rv = callback.getValueForField(fDef.getDataField('lotsaValuesDefault'))
        self.assertEqual(rv, 'one')

    def testCallbackEnumeratedMultiple(self):
        handle = self.getRbuildHandle(mock.MockObject())
        callback = handle.DescriptorConfig.callbackClass(handle.ui)
        fDef = handle.DescriptorConfig.descriptorClass()
        fDef.addDataField('lotsaValues',
            descriptions=[fDef.Description("foo")],
            multiple=True,
            type=fDef.EnumeratedType([
                fDef.ValueWithDescription('one',
                    descriptions=[fDef.Description("One")]),
                fDef.ValueWithDescription('two',
                    descriptions=[fDef.Description("Two")]),
            ]))
        fDef.addDataField('lotsaValuesDefault',
            descriptions=[fDef.Description("foo")],
            multiple=True,
            default=['two'],
            type=fDef.EnumeratedType([
                fDef.ValueWithDescription('one',
                    descriptions=[fDef.Description("One")]),
                fDef.ValueWithDescription('two',
                    descriptions=[fDef.Description("Two")]),
            ]))

        mock.mockMethod(handle.ui.getChoices)

        # field with no default
        handle.ui.getChoices._mock.setReturn([0],
            'Enter choice',
            ["One", "Two"], default=None)
        rv = callback.getValueForField(fDef.getDataField('lotsaValues'))
        self.assertEqual(rv, ['one'])

        # field with default
        handle.ui.getChoices._mock.setReturn([0],
            'Enter choice (blank for default)',
            ["One", "Two"], default=[1])
        rv = callback.getValueForField(fDef.getDataField('lotsaValuesDefault'))
        self.assertEqual(rv, ['one'])
