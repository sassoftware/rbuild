#
# Copyright (c) 2005-2008 rPath, Inc.
#
# This program is distributed under the terms of the Common Public License,
# version 1.0. A copy of this license should have been distributed with this
# source file in a file called LICENSE. If it is not present, the license
# is always available at http://www.rpath.com/permanent/licenses/CPL-1.0.
#
# This program is distributed in the hope that it will be useful, but
# without any warranty; without even the implied warranty of merchantability
# or fitness for a particular purpose. See the Common Public License for
# full details.
#

import sys, os
from rbuild import errors
from rbuild.pluginapi import command

from rbuild.facade import rbuilderfacade

class RbuilderBuildURLCommand(command.BaseCommand):
    """
    Shows all the urls related to a build
    """

    commands = ['build-url']
    help = 'Show all urls related to a build'
    paramHelp = '<buildId>'
    requireConfig = False

    #pylint: disable-msg=R0201,R0903
    # could be a function, and too few public methods
    def runCommand(self, handle, argSet, args):
        args = args[2:]
        if len(args) != 1:
            return self.usage()

        buildId = int(args[0])

        handle.facade.rbuilder.getBuildFiles(buildId)

        return 0

class RbuilderBuildWaitCommand(command.BaseCommand):
    """
    Waits for a build to finish building
    """

    commands = ['build-wait']
    help = 'Waits for a build to finish building'
    paramHelp = '<buildId>+'
    docs = {
        'timeout': "Time to wait before ending, even if the job is not done, 0 to wait indefinitely, default 0",
        'interval': 'Time, in seconds, between polling queries, default 30',
        }
    requireConfig = False

    def addLocalParameters(self, argDef):
        argDef['timeout'] = command.ONE_PARAM
        argDef['interval'] = command.ONE_PARAM

    #pylint: disable-msg=R0201,R0903
    # could be a function, and too few public methods
    def runCommand(self, handle, argSet, args):
        args = args[2:]
        if len(args) < 1:
            return self.usage()

        buildIds = [int(x) for x in args]

        timeout = int(argSet.pop('timeout', 0))
        interval = int(argSet.pop('interval', 30))
        quiet = handle.getConfig().quiet

        handle.facade.rbuilder.watchImages(buildIds, timeout=timeout, interval=interval, quiet=quiet)

        return 0

class RbuilderBuildProjectCommand(command.BaseCommand):
    '''
    Builds specified images for the specified product version and stage.
    Requires an rBuilder that supports building from Product Definition.
    '''

    commands = ['build-product', 'build-project']
    help = "create a new build from the version's product definition"
    paramHelp = '<product name> <version name> <stage>'
    docs = {
        'force':        'Continue running builds in the definition even if a previous one failed.',
        'timeout': "Time to wait before ending, even if the job is not done, 0 to wait indefinitely, default 0",
        'interval': 'Time, in seconds, between polling queries, default 30',
        'wait':         'Wait until a build finishes before returning',
        }
    requireConfig = False

    def addLocalParameters(self, argDef):
        argDef['force'] = command.NO_PARAM
        argDef['timeout'] = command.ONE_PARAM
        argDef['interval'] = command.ONE_PARAM
        argDef['wait'] = command.NO_PARAM

    #pylint: disable-msg=R0201,R0903
    # could be a function, and too few public methods
    def runCommand(self, handle, argSet, args):
        args = args[2:]
        if len(args) != 3:
            return self.usage()

        wait = argSet.pop('wait', False)
        timeout = int(argSet.pop('timeout', 0))
        interval = int(argSet.pop('interval', 30))
        quiet = handle.getConfig().quiet
        force = argSet.pop('force', False)

        productName = args[0]
        versionName = args[1]
        stageName = args[2]


        client = handle.facade.rbuilder._getRbuilderClient()
        buildIds = client.startProductBuilds(productName, versionName, stageName, force)
        if wait:
            handle.facade.rbuilder.watchImages(buildIds, timeout=timeout, interval=interval, quiet=quiet)
        else:
            print "Started builds %s" % str(buildIds)

        return 0


class RbuilderBuildCreateCommand(command.BaseCommand):
    '''
Available build types:

     installable_iso    Installable CD/DVD
        raw_fs_image    Raw Filesystem Image
             tarball    Compressed Tar File
            live_iso    Demo CD/DVD (Live CD/DVD)
        raw_hd_image    Raw Hard Disk Image
        vmware_image    VMware (R) Virtual Appliance
    vmware_esx_image    VMware (R) ESX Server Virtual Appliance
    virtual_pc_image    VHD for Microsoft (R) Hyper-V
             xen_ova    Citrix XenServer (TM) Appliance
        virtual_iron    Virtual Iron Virtual Appliance
                 ami    Amazon Machine Image (EC2)
          update_iso    Update CD/DVD
       appliance_iso    Appliance Installable ISO
           imageless    Online Update

Settings for --option='KEY VALUE':

  Common settings for raw_fs_image, tarball, raw_hd_image, vmware_image, vmware_esx_image, virtual_iron, virtual_pc_image, xen_ova:
    autoResolve         Automatically install required dependencies during updates
    baseFileName        Custom image file name (replaces name-version-arch)
    swapSize            How many MB swap space should be reserved in this image? (default: 128)
    installLabelPath    Custom Conary installLabelPath setting (leave blank for default)

  Installable CD/DVD Settings:
    autoResolve         Automatically install required dependencies during updates
    maxIsoSize          ISO Size (default: 681574400)
    bugsUrl             Bug report URL (default: http://issues.rpath.com/)
    media-template      media-template
    betaNag             This image is considered a beta
    anaconda-templates  anaconda-templates
    baseFileName        Custom image file name (replaces name-version-arch)
    anaconda-custom     anaconda-custom
    installLabelPath    Custom Conary installLabelPath setting (leave blank for default)
    showMediaCheck      Prompt to verify CD/DVD images during install

  Raw Filesystem Image Settings:
    freespace           How many MB of free space should be allocated in the image? (default: 250)

  Demo CD/DVD (Live CD/DVD) Settings:
    autoResolve         Automatically install required dependencies during updates
    installLabelPath    Custom Conary installLabelPath setting (leave blank for default)
    baseFileName        Custom image file name (replaces name-version-arch)
    zisofs              Compress filesystem (default: True)
    unionfs             Enable UnionFS for the entire filesystem. (For this option, the
                        UnionFS kernel module is required in the group. See rBuilder
                        documentation for more information on this option.)

  Raw Hard Disk Image Settings:
    freespace           How many MB of free space should be allocated in the image? (default: 250)

  VMware (R) Virtual Appliance Settings:
    freespace           How many MB of free space should be allocated in the image? (default: 250)
    natNetworking       Use NAT instead of bridged networking.
    vmMemory            How many MB of RAM should be allocated when this virtual machine is
                        started? (default: 256)
    diskAdapter         Which hard disk adapter should this image be built for? (default: lsilogic)
    vmSnapshots         Allow snapshots to be created

  VMware (R) ESX Server Virtual Appliance Settings:
    freespace           How many MB of free space should be allocated in the image? (default: 250)
    natNetworking       Use NAT instead of bridged networking.
    vmMemory            How many MB of RAM should be allocated when this virtual machine is
                        started? (default: 256)

  VHD for Microsoft (R) Hyper-V Settings:
    freespace           How many MB of free space should be allocated in the image? (default: 250)
    vhdDiskType         VHD hard disk type (default: dynamic)

  Citrix XenServer (TM) Appliance Settings:
    freespace           How many MB of free space should be allocated in the image? (default: 250)
    vmMemory            How many MB of RAM should be allocated when this virtual machine is
                        started? (default: 256)

  Virtual Iron Virtual Appliance Settings:
    freespace           How many MB of free space should be allocated in the image? (default: 250)
    vhdDiskType         VHD hard disk type (default: dynamic)

  Amazon Machine Image (EC2) Settings:
    autoResolve         Automatically install required dependencies during updates
    freespace           How many MB of free space should be allocated in the image? (default: 250)
    amiHugeDiskMountpoint       Mountpoint for scratch space (/dev/sda2) on AMI
    baseFileName        Custom image file name (replaces name-version-arch)
    installLabelPath    Custom Conary installLabelPath setting (leave blank for default)

  Update CD/DVD Settings:
    baseFileName        Custom image file name (replaces name-version-arch)
    media-template      media-template

  Appliance Installable ISO Settings:
    autoResolve         Automatically install required dependencies during updates
    bugsUrl             Bug report URL (default: http://issues.rpath.com/)
    media-template      media-template
    betaNag             This image is considered a beta
    anaconda-templates  anaconda-templates
    installLabelPath    Custom Conary installLabelPath setting (leave blank for default)
    anaconda-custom     anaconda-custom
    baseFileName        Custom image file name (replaces name-version-arch)
    showMediaCheck      Prompt to verify CD/DVD images during install

Note: all build types may not be supported by all rBuilder servers.
    '''

    commands = ['build-create']
    paramHelp = "<product name> <trove spec> <build type>"
    help = "create a single build by specifying all parameters"
    docs = {
        'build-notes':  'Set build notes',
        'build-notes-file':     'Set build notes from a file',
        'name':         'Set the build name',
        'option':       ('Set a build option', "'KEY VALUE'"),
        'timeout': "Time to wait before ending, even if the job is not done, 0 to wait indefinitely, default 0",
        'interval': 'Time, in seconds, between polling queries, default 30',
        'wait':         'Wait until a build finishes before returning',
        }

    def addLocalParameters(self, argDef):
        argDef["option"] = command.MULT_PARAM
        argDef["name"] = command.ONE_PARAM
        argDef["build-notes"] = command.ONE_PARAM
        argDef["build-notes-file"] = command.ONE_PARAM
        argDef['timeout'] = command.ONE_PARAM
        argDef['interval'] = command.ONE_PARAM
        argDef['wait'] = command.NO_PARAM


    def runCommand(self, handle, argSet, args):
        args = args[2:]
        if len(args) != 3:
            return self.usage()

        name = argSet.pop('name', None)
        wait = argSet.pop('wait', False)
        timeout = int(argSet.pop('timeout', 0))
        interval = int(argSet.pop('interval', 30))
        quiet = handle.getConfig().quiet
        if 'option' not in argSet:
            argSet['option'] = []

        productName, troveSpec, buildType = args

        buildOptions = dict(tuple(x.split(" ", 1)) for x in argSet['option'])

        # Note that we do not do any options validation here, as that requires
        # too much rbuilder code

        if 'build-notes' in argSet and 'build-notes-file' in argSet:
            raise errors.RbuildError('--build-notes and --build-notes-file may not '
                'be used together.')

        # resolve a trovespec
        res = handle.facade.conary._findTroves([troveSpec])

        n, v, f = res.values()[0][0]

        if not (n and v and f is not None):
            raise errors.RbuildError("Please specify a full trove spec in the form: <trove name>=<version>[<flavor>]\n" \
                "All parts must be fully specified. Use conary rq --full-versions --flavors <trove name>\n" \
                "to find a valid trove spec.")

        buildTroveVersion = v.freeze()
        buildTroveFlavor = f.freeze()

        #Set up the build notes
        buildNotes = ''
        if 'build-notes' in argSet:
            buildNotes = argSet['build-notes']
        if 'build-notes-file' in argSet:
            fn = argSet['build-notes-file']
            if os.path.exists(fn):
                buildNotes = open(fn).read()
        #Set up the call to start the job
        buildId = handle.facade.rbuilder.createImage(productName, n, buildTroveVersion,
                buildTroveFlavor, buildType, name, buildNotes, buildOptions)

        if wait:
            handle.facade.rbuilder.watchImages([buildId], timeout=timeout, interval=interval, quiet=quiet)
        return 0
