#!/bin/sh
RBUILD_PATH=$(ls -d $(dirname $0/..))
export PYTHONPATH=$RBUILD_PATH:$RMAKE_PATH:$CONARY_PATH
epydoc --html -o docs -v --name rBuild rbuild
