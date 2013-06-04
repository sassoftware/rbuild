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
        cfg = handle.RbuildHandle.configClass(readConfigFiles=True)

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
