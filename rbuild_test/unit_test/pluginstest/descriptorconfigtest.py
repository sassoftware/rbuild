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
            _ddata, dc.callbackClass(), retry=True)
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
            descriptions=[fDef.Description("foodef")],
            default=['two'],
            type=fDef.EnumeratedType([
                fDef.ValueWithDescription('one',
                    descriptions=[fDef.Description("One")]),
                fDef.ValueWithDescription('two',
                    descriptions=[fDef.Description("Two")]),
            ]))

        mock.mockMethod(handle.ui.getChoice)
        mock.mockMethod(handle.ui.getTerminalSize, (24, 80))

        # field with no default
        handle.ui.getChoice._mock.setReturn(0,
            'Enter choice', ["One", "Two"], default=None,
            prePrompt="Pick foo:", pageSize=21)
        rv = callback.getValueForField(fDef.getDataField('lotsaValues'))
        self.assertEqual(rv, 'one')

        # field with default
        handle.ui.getChoice._mock.setReturn(0,
            'Enter choice (blank for default)', ["One", "Two"], default=1,
            prePrompt="Pick foodef:", pageSize=21)
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
            descriptions=[fDef.Description("foodef")],
            multiple=True,
            default=['two'],
            type=fDef.EnumeratedType([
                fDef.ValueWithDescription('one',
                    descriptions=[fDef.Description("One")]),
                fDef.ValueWithDescription('two',
                    descriptions=[fDef.Description("Two")]),
            ]))

        mock.mockMethod(handle.ui.getChoices)
        mock.mockMethod(handle.ui.getTerminalSize, (24, 80))

        # field with no default
        handle.ui.getChoices._mock.setReturn([0], 'Enter choice',
            ["One", "Two"], default=None, prePrompt="Pick foo:",
            pageSize=21)
        rv = callback.getValueForField(fDef.getDataField('lotsaValues'))
        self.assertEqual(rv, ['one'])

        # field with default
        handle.ui.getChoices._mock.setReturn([0],
            'Enter choice (blank for default)', ["One", "Two"], default=[1],
            prePrompt="Pick foodef:", pageSize=21)
        rv = callback.getValueForField(fDef.getDataField('lotsaValuesDefault'))
        self.assertEqual(rv, ['one'])

    def testCallbackDescriptorWithListType(self):
        handle = self.getRbuildHandle(mock.MockObject())
        callback = handle.DescriptorConfig.callbackClass(handle.ui)
        dsc1 = handle.DescriptorConfig.descriptorClass()
        dsc1.setId("apache-configuration/process-info")
        dsc1.setRootElement("blabbedy-blah")
        dsc1.setDisplayName('Process Ownership Information')
        dsc1.addDescription('Process Ownership Information')
        dsc1.addDataField("user", type="str", default="apache", required=True,
                descriptions="User")
        dsc1.addDataField("group", type="str", default="apache", required=True,
                descriptions="Group")

        vhost = handle.DescriptorConfig.descriptorClass()
        vhost.setId("apache-configuration/vhost")
        vhost.setRootElement('vhost')
        vhost.setDisplayName('Virtual Host Configuration')
        vhost.addDescription('Virtual Host Configuration')
        vhost.addDataField('serverName', type="str", required=True,
                descriptions="Virtual Host Name")
        vhost.addDataField('documentRoot', type="str", required=True,
                descriptions="Virtual Host Document Root")

        dsc = handle.DescriptorConfig.descriptorClass()
        dsc.setId("apache-configuration")
        dsc.setDisplayName('Apache Configuration')
        dsc.addDescription('Apache Configuration')

        dsc.addDataField('port', type="int",
                required=True, descriptions="Apache Port")
        dsc.addDataField('processInfo', type=dsc.CompoundType(dsc1),
                required=True, descriptions="Process Ownership Information")
        dsc.addDataField('vhosts', type=dsc.ListType(vhost),
                required=True, descriptions="Virtual Hosts",
                constraints=[
                    dict(constraintName='uniqueKey', value="serverName"),
                    dict(constraintName="minLength", value=1)])

        #mock.mockMethod(handle.ui.write)
        #mock.mockMethod(handle.ui.writeError)
        mock.mockMethod(handle.ui.input)
        i = handle.ui.input
        i._mock.setReturn('8081',
                'Enter Apache Port [required] (type int): ')
        i._mock.setReturn('nobody',
                'Enter User [required] (type str) (Default: apache): ')
        i._mock.setReturn('nobody',
                'Enter Group [required] (type str) (Default: apache): ')
        i._mock.setReturn('a.org',
                'Enter Virtual Host Name [required] (type str): ')
        i._mock.setReturn('/srv/www/a',
                'Enter Virtual Host Document Root [required] (type str): ')
        i._mock.setReturn('N',
                'More items for: vhosts (Virtual Hosts) (Default: Y): ')

        descriptorData = dsc.createDescriptorData(callback)
        self.assertXMLEquals(descriptorData.toxml(), """
<descriptorData version="1.1">
  <port>8081</port>
  <processInfo>
    <user>nobody</user>
    <group>nobody</group>
  </processInfo>
  <vhosts list="true">
    <vhost>
      <serverName>a.org</serverName>
      <documentRoot>/srv/www/a</documentRoot>
    </vhost>
  </vhosts>
</descriptorData>
""")

    def testCallbackWarning(self):
        handle = self.getRbuildHandle(mock.MockObject())
        callback = handle.DescriptorConfig.callbackClass(handle.ui)
        dsc = handle.DescriptorConfig.descriptorClass()
        dsc.setId("apache-configuration")
        dsc.setDisplayName('Apache Configuration')
        dsc.addDescription('Apache Configuration')

        dsc.addDataField('port', type="int",
                required=True, descriptions="Apache Port",
                # add a constraint that 8081 is the only legal value
                constraints=[
                    dict(constraintName='legalValues', values=[8081])
                    ]
                )

        mock.mockMethod(handle.ui.warning)
        mock.mockMethod(handle.ui.input)
        i = handle.ui.input
        # return 80 from the prompt the first time, then 8081
        i._mock.setReturns(['80', '8081'],
                'Enter Apache Port [required] (type int): ')

        descriptorData = dsc.createDescriptorData(callback, retry=True)
        handle.ui.warning._mock.assertCalled("'Apache Port': '80' is not a legal value")
        self.assertXMLEquals(descriptorData.toxml(), """
<descriptorData version="1.1">
  <port>8081</port>
</descriptorData>
""")

    def testBooleanInput(self):
        handle = self.getRbuildHandle(mock.MockObject())
        callback = handle.DescriptorConfig.callbackClass(handle.ui)
        fDef = handle.DescriptorConfig.descriptorClass()
        fDef.addDataField('boolValue', type="bool", descriptions="Bool Value")
        mock.mockMethod(handle.ui.warning)
        mock.mockMethod(handle.ui.input)

        handle.ui.input._mock.setReturns(["aaa", "true"],
            "Enter Bool Value (type bool): ")
        ddata = fDef.createDescriptorData(callback)
        handle.ui.warning._mock.assertCalled(
            "Input must be in the form yes, no, true, or false")
        self.assertXMLEquals(ddata.toxml(), """
<descriptorData version="1.1">
  <boolValue>True</boolValue>
</descriptorData>
""")
