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
targets
'''
from rbuild import errors
from rbuild import pluginapi
from rbuild.pluginapi import command


class CreateTargetCommand(command.BaseCommand):
    help = 'Create a target on a SAS App Engine'
    paramHelp = '<TYPE>'
    docs = {'list': 'List available target types',
            'from-file': 'Load config from file',
            'to-file': 'Write config to file',
            }

    def addLocalParameters(self, argDef):
        argDef['list'] = '-l', command.NO_PARAM
        argDef['from-file'] = '-f', command.ONE_PARAM
        argDef['to-file'] = '-o', command.ONE_PARAM

    def runCommand(self, handle, argSet, args):
        ui = handle.ui
        rb = handle.facade.rbuilder

        list_types = argSet.pop('list', False)
        fromFile = argSet.pop('from-file', None)
        toFile = argSet.pop('to-file', None)

        if list_types:
            types = rb.getTargetTypes().keys()
            ui.write("Available target types: %s" % ', '.join(types))
            return

        if fromFile:
            handle.DescriptorConfig.readConfig(fromFile)

        _, targetType = self.requireParameters(args, expected=['TYPE'])
        target = handle.Targets.createTarget(targetType)
        handle.Targets.configureTargetCredentials(target)

        if toFile:
            handle.DescriptorConfig.writeConfig(toFile)


class DeleteTargetsCommand(command.BaseCommand):
    help = 'Delete targets'
    paramHelp = '<target id>+'

    def runCommand(self, handle, argSet, args):
        _, targetIds = self.requireParameters(
            args, expected=['ID'], appendExtra=True)
        for targetId in targetIds:
            handle.Targets.delete(targetId)


class EditTargetCommand(command.BaseCommand):
    '''
    Edit targets
    '''
    help = 'Edit target configuration'
    commands = ['target']
    paramHelp = '<target id>'
    docs = {
        'from-file': 'Load target config from a file',
        'to-file': 'Write target config to a file',
        }

    def addLocalParameters(self, argDef):
        argDef['from-file'] = '-f', pluginapi.command.ONE_PARAM
        argDef['to-file'] = '-o', pluginapi.command.ONE_PARAM

    def runCommand(self, handle, argSet, args):
        fromFile = argSet.pop('from-file', None)
        toFile = argSet.pop('to-file', None)

        _, targetName, targetType = self.requireParameters(args,
            expected='NAME', allowExtra=True)

        if fromFile:
            handle.DescriptorConfig.readConfig(fromFile)

        handle.Targets.edit(targetName, targetType[0] if targetType else None)

        if toFile:
            handle.DescriptorConfig.writeConfig(toFile)


class ListTargetsCommand(command.ListCommand):
    help = 'list targets'
    resource = 'targets'
    listFields = ('target_id', 'name', 'description', 'is_configured',
                  'credentials_valid')
    listFieldMap = dict(
        is_configured=dict(display_name='Configred'),
        credentials_valid=dict(display_name='Credentials'),
        )


class Targets(pluginapi.Plugin):
    name = 'targets'

    def createTarget(self, targetType):
        '''
            Create a target

            @param targetType: type of target to create
            @type targetType: str
            @return: configured target
            @rtype: rObj(target)
        '''
        dc = self.handle.DescriptorConfig
        rb = self.handle.facade.rbuilder

        descriptor_xml = rb.getTargetDescriptor(targetType)
        if descriptor_xml is None:
            raise errors.PluginError('No such target type: %s' % targetType)

        ddata = dc.createDescriptorData(fromStream=descriptor_xml)

        target = rb.createTarget(ddata, targetType)
        rb.configureTarget(target, ddata)
        return target

    def configureTargetCredentials(self, target):
        '''
            Set credentials on a target

            @param target: target to set credentials for
            @type target: rObj(target)
            @return: target with credentials Set
            @rtype: rObj(target)
        '''
        dc = self.handle.DescriptorConfig
        rb = self.handle.facade.rbuilder

        for action in target.actions:
            if 'credentials' in action.name:
                ddata = dc.createDescriptorData(fromStream=action.descriptor)
                try:
                    rb.configureTargetCredentials(target, ddata)
                except errors.RbuildError as e:
                    self.handle.ui.warning(str(e))
                return
        errors.PluginError('Unable to find credentials action on this target')

    def delete(self, targetId):
        target = self.handle.facade.rbuilder.getTargets(target_id=targetId)
        if target:
            target[0].delete()
        else:
            self.handle.ui.write("No target found with id '%s'" % targetId)

    def edit(self, targetName, targetType=None):
        dc = self.handle.DescriptorConfig
        rb = self.handle.facade.rbuilder
        ui = self.handle.ui

        target = rb.getTargets(name=targetName)
        if target:
            if len(target) > 1:
                if targetType:
                    target = [t for t in target
                              if t.target_type.name == targetType][0]
                else:
                    ui.write('Ambiguous target name')
                    response = ui.getChoice('Pick a target', pageSize=10,
                        choices=['%s (%s)' % (t.name, t.target_type.name)
                                 for t in target])
                    target = target[response]
            else:
                target = target[0]
        else:
            msg = "No target found with name '%s'" % targetName
            if targetType:
                msg = ' '.join([msg, "and type '%s'" % targetType])
            raise errors.PluginError(msg)

        if rb.isAdmin(self.handle.getConfig().user[0]):
            currentValues = dict((e, getattr(target.target_configuration, e))
                                 for e in target.target_configuration.elements)
            descriptor = rb.getTargetDescriptor(target.target_type.name)
            ddata = dc.createDescriptorData(
                fromStream=descriptor, defaults=currentValues)
            target = rb.configureTarget(target, ddata)
        self.configureTargetCredentials(target)

    def initialize(self):
        self.handle.Commands.getCommandClass('create').registerSubCommand(
            'target', CreateTargetCommand)
        self.handle.Commands.getCommandClass('delete').registerSubCommand(
            'targets', DeleteTargetsCommand)
        self.handle.Commands.getCommandClass('edit').registerSubCommand(
            'target', EditTargetCommand)
        self.handle.Commands.getCommandClass('list').registerSubCommand(
            'targets', ListTargetsCommand)

    def list(self, *args, **kwargs):
        return self.handle.facade.rbuilder.getTargets()
