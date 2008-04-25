#
# Copyright (c) 2006-2008 rPath, Inc.
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
"""
    Constants that are only relevant to rbuild internals
"""

# TODO: would be nice if we could get this data from a server api
# At that point, this should move out of constants
# Note: this might belong in the buildimages plugin directly
VALID_BUILD_TYPES = {
    'BOOTABLE_IMAGE'    : 0,
    'INSTALLABLE_ISO'   : 1,
    'STUB_IMAGE'        : 2,
    'RAW_FS_IMAGE'      : 3,
    'NETBOOT_IMAGE'     : 4,
    'TARBALL'           : 5,
    'LIVE_ISO'          : 6,
    'RAW_HD_IMAGE'      : 7,
    'VMWARE_IMAGE'      : 8,
    'VMWARE_ESX_IMAGE'  : 9,
    'VIRTUAL_PC_IMAGE'  : 10,
    'XEN_OVA'           : 11,
    'VIRTUAL_IRON'      : 12,
    'PARALLELS'         : 13,
    'AMI'               : 14,
    'UPDATE_ISO'        : 15,
    'APPLIANCE_ISO'     : 16,
}
