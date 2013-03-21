#!/bin/sh -x
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
