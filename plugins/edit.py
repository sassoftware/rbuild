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
Edit product definition
"""
import os
import tempfile
import subprocess
import StringIO

from lxml import etree
from xobj import xobj

from rbuild import errors, pluginapi


class EditCommand(pluginapi.command.CommandWithSubCommands):
    """
    Edit product definition
    """
    commands = ['edit']
    help = 'Edit product definition'


class EditProductCommand(pluginapi.command.BaseCommand):
    """
    Edit product definition XML
    """
    help = 'Edit product definition XML'
    commands = ['product']
    docs = {
            'message' : 'Text describing why the commit was performed',
    }

    def addLocalParameters(self, argDef):
        argDef['message'] = '-m', pluginapi.command.ONE_PARAM

    def runCommand(self, handle, argSet, _):
        """
        Process the command line provided for this plugin
        @param handle: context handle
        @type handle: rbuild.handle.RbuildHandle
        """
        message = argSet.pop('message', 'rbuild commit')
        handle.Edit.editProductDefinition(message)


class EditImageDefCommand(pluginapi.command.BaseCommand):
    """
    Edit image definitions
    """
    help = 'Edit image definition'
    commands = ['imagedef']
    paramHelp = '<NAME>'
    docs = {
        'from-file': 'Load image defintion config from a file',
        'to-file': 'Write image definition config to a file',
        'message': 'Text describing why the commit was performed',
        }

    def addLocalParameters(self, argDef):
        argDef['list'] = '-l', pluginapi.command.NO_PARAM
        argDef['from-file'] = '-f', pluginapi.command.ONE_PARAM
        argDef['to-file'] = '-o', pluginapi.command.ONE_PARAM
        argDef['message'] = '-m', pluginapi.command.ONE_PARAM

    def runCommand(self, handle, argSet, args):
        ui = handle.ui
        try:
            pd = handle.product
        except AttributeError:
            raise errors.PluginError('Must be in an rbuild checkout')

        message = argSet.pop('message', None)
        listImageDefs = argSet.pop('list', False)
        fromFile = argSet.pop('from-file', None)
        toFile = argSet.pop('toFile', None)

        stageName = handle.productStore._currentStage
        if stageName:
            buildDefs = pd.getBuildsForStage(stageName)
        else:
            buildDefs = pd.getBuildDefinitions()

        if listImageDefs:
            ui.write('Available image defintions:\n %s' %
                     '\n '.join(bd.name for bd in buildDefs))
            return

        _, imageDefName = self.requireParameters(args, expected='NAME')

        if fromFile:
            handle.DescriptorConfig.readConfig(fromFile)

        buildDef = None
        for bd in buildDefs:
            if bd.name == imageDefName:
                buildDef = bd
                break

        if buildDef is None:
            raise errors.PluginError(
                "Cound not find image definition '%s'" % imageDefName)

        handle.Edit.editImageDefinition(buildDef, message)

        if toFile:
            handle.DescriptorConfig.writeConfig(toFile)


class Edit(pluginapi.Plugin):
    """
    Edit plugin
    """
    name = 'edit'

    def registerCommands(self):
        """
        Register the command-line handling portion of the update plugin.
        """
        self.handle.Commands.registerCommand(EditCommand)
        self.handle.Commands.getCommandClass('edit').registerSubCommand(
            'product', EditProductCommand)
        self.handle.Commands.getCommandClass('edit').registerSubCommand(
            'imagedef', EditImageDefCommand)

    def editImageDefinition(self, buildDef, message):
        dc = self.handle.DescriptorConfig
        pd = self.handle.product
        ps = self.handle.productStore
        rb = self.handle.facade.rbuilder

        oldName = buildDef.name

        currentValues = dict(('options.%s' % k, v)
                             for k, v in vars(buildDef.image).items())
        currentValues['displayName'] = buildDef.name

        imageTypeDef = rb.getImageTypeDef(buildDef.containerTemplateRef,
                                          buildDef.architectureRef)

        descriptor = xobj.toxml(imageTypeDef.descriptor._root)
        ddata = dc.createDescriptorData(
            fromStream=descriptor, defaults=currentValues)

        for field in ddata.getFields():
            fname = field.getName().strip('options.')
            fvalue = field.getValue()
            if fname == 'displayName':
                fname = 'name'
                set_func = getattr(buildDef, 'set_%s' % fname, None)
            else:
                set_func = getattr(buildDef.image, 'set_%s' % fname, None)
            if set_func:
                set_func(fvalue)

        with open(ps.getProductDefinitionXmlPath(), 'w') as fh:
            pd.serialize(fh)

        if message is None:
            message = 'Update image definition %s' % oldName
        ps.commit(message=message)
        ps.update()

    def editProductDefinition(self, message):
        handle = self.handle
        tmpf = self._makeTemporaryFile()

        try:
            handle.product.serialize(tmpf)
        except Exception:
            handle.ui.writeError("Command run outside of expected context, "
                                 "make sure you're in a checkout directory.")
            return 1
        tmpf.flush()
        try:
            checkModified = True
            while 1:
                ret = self._editProductDefinitionFile(handle, tmpf,
                        checkModified=checkModified)
                checkModified = False
                if ret < 0:
                    # -1 means no change, so return 0 in that case
                    return int(ret != -1)
                if ret == 0:
                    break
                while 1:
                    retry = handle.ui.input("Do you want to retry? (Y/n) ")
                    retry = retry.strip().lower()
                    if not retry:
                        retry = 'y'
                    if retry == 'n':
                        return ret
                    if retry == 'y':
                        break
        finally:
            # Cleanup here
            pass
        # We now have a changed product definition loaded
        # Serialize it
        handle.product.serialize(
                file(handle.productStore.getProductDefinitionXmlPath(), "w"))
        # And commit
        handle.productStore.commit(message=message)
        return 0

    @classmethod
    def _makeTemporaryFile(cls):
        return tempfile.NamedTemporaryFile(suffix='.xml')

    def _fileSignature(self, stream):
        st = os.fstat(stream.fileno())
        return (st.st_mtime, st.st_size)

    def _editProductDefinitionFile(self, handle, stream, checkModified=False):
        """
        @return: 0 if file was successfully modified
            > 0: error, should retry
             -1: file not modified, and checkModified is True
            < -1: error, should NOT retry
        """
        stream.seek(0)
        if checkModified:
            oldFileSignature = self._fileSignature(stream)
        ret = self._invokeEditor(stream)
        if ret != 0:
            handle.ui.info("Edit failed")
            return -100
        if checkModified and self._fileSignature(stream) == oldFileSignature:
            handle.ui.info("Nothing changed")
            return -1
        # Load new proddef, validating it too
        stream.seek(0)
        try:
            doc = etree.parse(stream)
            # Extract namespace
            root = doc.getroot()
            ns = root.nsmap.get(None)
            if ns is None:
                handle.ui.writeError("Expected namespaced document")
                return 1
            pdVersion = root.attrib.get('version')
            if pdVersion is None:
                handle.ui.writeError("Expected versioned document")
                return 2
            stream.seek(0)
            # Schema validation
            handle.product.__class__.validate(stream,
                    handle.product.schemaDir, pdVersion)
            stream.seek(0)
            handle.product.__init__(fromStream=stream,
                    schemaDir=handle.product.schemaDir, validate=True)
            handle.product.serialize(StringIO.StringIO(), validate=True)
            return 0
        except etree.Error, e:
            handle.ui.writeError("Error: %s", str(e))
            return 3
        except handle.productStore.proddef.ProductDefinitionError, e:
            handle.ui.writeError("Error: %s", str(e))
            return 4
        except Exception, e:
            handle.ui.writeError("Error: %s", str(e))
            return 5

    def _invokeEditor(self, stream):
        editor = os.getenv('VISUAL')
        if editor is None:
            editor = os.getenv('EDITOR', 'vi')
        p = subprocess.Popen([editor, stream.name])
        p.communicate()
        return p.returncode
