#
# Copyright (c) rPath, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#


# NOTE -- this is (currently) a copy of the module in rpath-tools
# at some point in the future this should be moved into a common
# lib.

import urllib2
import urlparse
from lxml import etree as ET
from conary.lib.compat import namedtuple

ApiFinderResult = namedtuple('ApiFinderResult', ['version', 'url'])

class ApiFinder(object):
    '''
    Determines an rBuilder service location in a API version agnostic
    way.   Example: 

    results = ApiFinder('dhcp244.eng.rpath.com').url('inventory')
    results.version
    results.url

    The latest version matching the constraints will always be returned.

    minVersion and maxVersion can be set to exclude using a future
    version or a "too old" version. 

    For SSL usage, for instance from rpath-register (which must proxy)
    pass in an appropriate OpenerDirector otherwise urllib2 will be used, 
    making things usuable with a RUS but sufficient for direct access.
    '''

    def __init__(self, server, opener=None, secure=False,
        minVersion=0, maxVersion=99999):
        self.server = server
        self.tipData = None
        self.secure = secure
        self.opener = opener
        if minVersion is None:
            minVersion = 0
        if maxVersion is None:
            maxVersion = 999999
        self.minVersion = minVersion
        self.maxVersion = maxVersion

    def _read(self, url):
        ''' 
        GET a URL, using the OpenerDirector if supplied.
        '''
        url = self._secureUrl(url)
        if self.opener:
            return self.opener.open(url).read()
        else:
            return urllib2.urlopen(url).read()

    def _secureUrl(self, url):
        '''
        When running through a RUS, the self discovery
        URLs need modification.
        '''
        if self.secure:
            return url.replace("http://","https://")
        return url

    def url(self, purpose):
        '''
        Retrieves a url for a specific service function
        '''

        versioned = False
        number = False
        if self.tipData is None:
            versioned, number, self.tipData = self._findTip()

        doc = ET.fromstring(self.tipData) 

        if not purpose:
            found = doc
        else:
            found = doc.find(purpose)
            if found is None:
                raise Exception("element not found: %s" % found)

        result = found.attrib.get('id', None)
        if result is None:
            # older API versions don't label elements with 'id'
            result = found.attrib['href']
        url = self._secureUrl(result)

        return ApiFinderResult(version=number, url=url)

    def _bestVersion(self, versionElts):
        '''
        Returns (version, URL) for the closest matching version to the
        specified version.  Will possibly try an older version, never
        a newer version.
        '''
        versions = {}
        # convert list of XML api_version elements
        # who have attributes name='v1', name='v2', etc
        # to a dict of version number -> elements
        def toVersionNum(x):
            return int(x.attrib['name'].replace('v',''))
        versions = dict( [ (toVersionNum(x), x) for x in versionElts ] )
        versionNums = versions.keys()
        versionNums.sort()
        versionNums.reverse()
        for x in versionNums:
            if x >= self.minVersion and x <= self.maxVersion:
                return (x, versions[x].attrib['id'])
        raise Exception("unable to find a compatible API version %s<x<%s" % (
            self.minVersion, self.maxVersion))

    def _findTip(self):
        '''
        Finds the document that describes the services endpoints.
        Returns tuple of whether the API is versioned or not (v0)
        and the data from that document.
        '''
        url = urlparse.urlunsplit(['http', self.server, 'api', None, None])

        tipData = self._read(url)
        doc = ET.fromstring(tipData)
        number = 0
        if doc.tag == 'api':
            # API is versioned, return highest if multiple supported
            tipUrl = None
            versionsCol = doc.find("api_versions")
            versions = versionsCol.findall("api_version")
            number, tipUrl = self._bestVersion(versions)
            tipData = self._read(tipUrl)
            return (True, number, tipData)
        elif doc.tag == 'rbuilderStatus':
            # initial unversioned API, return this document directly
            return (False, number, tipData)
