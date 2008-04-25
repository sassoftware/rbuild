import os
import sys
sys.path.insert(0, os.environ['CONARY_PATH'])
sys.path.insert(0, os.environ['RMAKE_PATH'])
sys.path.insert(0, os.environ['RBUILD_PATH'])

from rbuild.internal import pluginloader
pluginDir = os.path.realpath(os.environ['RBUILD_PATH'] + '/plugins')
plugins = pluginloader.getPlugins([], [pluginDir])
plugins.loader.install()
