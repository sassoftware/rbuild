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


"""
Implements the API for initializing an rbuild handle from python.

This API is currently ALPHA and subject to change, even entire
replacement.

Example::
    from rbuild import api1
    handle = api1.getHandle()
    handle.ui.write('hello, world!')

That will work as long as api1 is preserved.

The latest API will be exposed as rbuild, so you can also do::
    import rbuild
    handle = rbuild.getHandle()
    handle.ui.write('hello, world!')

That will work as long as the semantics of C{getHandle()} are preserved.
"""

from rbuild import handle
from rbuild import rbuildcfg
from rbuild.internal import pluginloader
from rbuild.productstore import abstract, dirstore


def getHandle(dirName=None, prodDefLabel=None):
        """
        Initializes an rBuild handle object, with a product definition
        as defined by the C{dirName} parameter (which provides a
        C{dirstore.CheckoutProductStore} product store) or the
        C{prodDefLabel} parameter (which provides a more limited
        C{abstract.ProductStore} product store that is insufficient
        for many plugin operations).  If no parameter is specified,
        a  C{dirstore.CheckoutProductStore} product store is provided
        based on the current directory.

        @param dirName: (None) directory for product store
        @param prodDefLabel: (None) label for product definition.
        @return: C{handle} instance
        """
        cfg = rbuildcfg.RbuildConfiguration(readConfigFiles=True)

        if prodDefLabel:
            productStore=None
        else:
            # note that if dirName is None, this defaults to current directory
            productStore = dirstore.CheckoutProductStore(baseDirectory=dirName)

        plugins = pluginloader.getPlugins([], cfg.pluginDirs)
        h = handle.RbuildHandle(cfg=cfg, pluginManager=plugins,
                                productStore=productStore)

        if prodDefLabel:
            productStore = abstract.ProductStore()
            product = productStore.getProduct()
            client = h.facade.conary._getConaryClient()
            stream, _ = product._getStreamFromRepository(client, prodDefLabel)
            stream.seek(0)
            product.parseStream(stream)

        return h
