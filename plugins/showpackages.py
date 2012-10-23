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


from rbuild import errors
from rbuild import pluginapi
from rbuild.pluginapi import command

class ShowPackagesCommand(command.BaseCommand):
    help = 'show latest packages'

    #pylint: disable-msg=R0201,R0903,W0613
    # could be a function, and too few public methods,unused arguments
    def runCommand(self, handle, argSet, args):
        self.requireParameters(args)
        handle.ShowPackages.showPackageStatus()

class ShowPackages(pluginapi.Plugin):
    name = 'showpackages'

    def initialize(self):
        self.handle.Commands.getCommandClass('show').registerSubCommand(
                                            'packages', ShowPackagesCommand)

    def showPackageStatus(self):
        jobId = self.handle.productStore.getPackageJobId()
        if not jobId:
            raise errors.PluginError(
                        'No packages have been built in this environment')
        self.handle.Show.showJobStatus(jobId)
        return jobId
