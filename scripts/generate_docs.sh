#!/bin/sh -x
RBUILD_PATH=$(ls -d $(dirname $0)/..)
export PYTHONPATH=$RBUILD_PATH:$RMAKE_PATH:$CONARY_PATH:$PRODUCT_DEFINITION_PATH
epydoc --verbose --html --config docs/config/epydoc rbuild plugins
