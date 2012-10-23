#!/bin/sh -x
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


[ -d "$RBUILD_PATH" ] || RBUILD_PATH=$(ls -d $(dirname $0)/../)
[ -d "$RBUILD_PATH" ] || { echo "Could not find rbuild";exit 1; }
[ -d "$RMAKE_PATH" ] || RMAKE_PATH=$(ls -d $(dirname $0)/../../rmake)
[ -d "$RMAKE_PATH" ] || { echo "Could not find rmake";exit 1; }
[ -d "$XMLLIB_PATH" ] || XMLLIB_PATH=$(ls -d $(dirname $0)/../../rpath-xmllib)
[ -d "$XMLLIB_PATH" ] || { echo "Could not find rpath-xmllib";exit 1; }
[ -d "$CONARY_PATH" ] || CONARY_PATH=$(ls -d $(dirname $0)/../../conary)
[ -d "$CONARY_PATH" ] || { echo "Could not find conary";exit 1; }
[ -d "$PRODUCT_DEFINITION_PATH" ] || PRODUCT_DEFINITION_PATH=$(ls -d $(dirname $0)/../../rpath-product-definition)
[ -d "$PRODUCT_DEFINITION_PATH" ] || { echo "Could not find rpath-product-definition";exit 1; }
export PYTHONPATH=$RBUILD_PATH:$RMAKE_PATH:$CONARY_PATH:$PRODUCT_DEFINITION_PATH:$XMLLIB_PATH
epydoc --verbose --html --config docs/config/epydoc rbuild rbuild_plugins
