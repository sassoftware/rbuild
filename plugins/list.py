#
# Copyright (c) SAS Institute, Inc.
#

from rbuild import errors
from rbuild import pluginapi
from rbuild.pluginapi import command


class ListCommand(command.CommandWithSubCommands):
    help = 'List objects associated with the rbuilder'
    commands = [ 'list', ]


class ListImagesCommand(command.BaseCommand):
    help = 'list images'

    def runCommand(self, handle, argSet, args):
        filters = argSet.pop('filter', None)
        self.requireParameters(args)
        handle.List.listImages(filters)


class List(pluginapi.Plugin):
    name = 'list'

    def registerCommands(self):
        self.handle.Commands.registerCommand(ListCommand)
        self.handle.Commands.getCommandClass('list').registerSubCommand(
            'images', ListImagesCommand)

    def listImages(self, fitlers=None):
        self.handle.Build.checkProductStore()
        project = self.handle.product.getProductName()
        branch = self.handle.product.getBaseLabel()
        try:
            stage = self.handle.productStore.getActiveStageName()
        except errors.RbuildError as err:
            if 'No current stage' in str(err):
                stage = None
            else:
                raise

        images = self.handle.facade.rbuilder.getImages(
            project=project, branch=branch, stage=stage)
        if not images:
            self.handle.ui.write('No images found')
            return
        headers = ('ID', 'Name', 'Type', 'Status', 'Downloads')

        def data_generator():
            data = []
            for image in images:
                if image.status == '300':
                    status = 'Succeeded'
                elif image.status == '100':
                    status = 'Building'
                else:
                    status = 'Failed'

                downloads = ', '.join(f.url for f in image.files)
                data.append((image.image_id, image.name,
                             image.image_type.name, status, downloads))
            return data

        self.handle.ui.writeTable(data_generator(), headers)
