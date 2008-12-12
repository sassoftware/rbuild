#
# Copyright (c) 2008 rPath, Inc.
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

import sys
import urllib
import urlparse
from rbuild.facade import rbuilderfacade
from rbuild.pluginapi import command


class RbuilderCommand(command.BaseCommand):
    """
    Base class for rBuilder commands.

    Handles backwards-compatibility for some command-line options.
    """

    requireConfig = False

    def processLocalConfigOptions(self, rbuildConfig, argSet):
        """
        Tweak the serverUrl option so URLs that used to work with the
        old client continue to work with rBuild.
        """
        uri = rbuildConfig.serverUrl
        if not uri:
            return
        scheme, netloc, path, query, fragment = urlparse.urlsplit(uri)

        pathParts = path.split('/')
        if 'xmlrpc-private' in pathParts:
            # Remove xmlrpc-private; rbuild expects it not to be there
            # but the old client needed it.
            del pathParts[pathParts.index('xmlrpc-private'):]
        path = '/'.join(pathParts)

        userPart, hostPart = urllib.splituser(netloc)
        if userPart is not None:
            user, password = urllib.splitpasswd(userPart)
            rbuildConfig['user'] = (user, password)

        # Re-form URI sans user part
        uri = urlparse.urlunsplit((scheme, hostPart, path, query, fragment))
        rbuildConfig['serverUrl'] = uri
