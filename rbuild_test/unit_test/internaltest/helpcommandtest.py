#!/usr/bin/python
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



from rbuild_test import rbuildhelp

from rbuild.pluginapi import command
from rbuild.internal import main, helpcommand

# method runCommand is abstract - that's ok.
#pylint: disable-msg=W0223
class FooCommand(command.BaseCommand):
    """Long help text goes here"""
    commands = ['foo']
    help = 'bar'

class FooSubCommand(command.CommandWithSubCommands):
    """Long help text goes here"""
    commands = ['foo']
    help = 'bar'
    _subCommands = {'subCommand1' : None}

class HelpCommandTest(rbuildhelp.RbuildHelper):
    def testHelp(self):
        mainHandler = main.RbuildMain()
        mainHandler.registerCommand(FooCommand)
        cmd = helpcommand.HelpCommand()
        cmd.setMainHandler(mainHandler)
        rc, txt = self.captureOutput(cmd.runCommand, None, {}, 
                                     ['rbuild', 'help'])
        self.assertEquals(rc, 0)
        assert(txt == '''\
rbuild: Conary-based Product Development Tool

Common Commands
  foo   bar

Information Display
  help  Display help information
''')
        rc, txt = self.captureOutput(cmd.runCommand, None, {}, 
                                     ['rbuild', 'help', 'foo'])
        self.assertEquals(rc, 0)
        txt = txt.replace('usage', 'Usage') #difference between 2.4/2.5
        txt = txt.replace('options', 'Options') #difference between 2.4/2.5
        assert(txt == '''\
Usage: rbuild foo 

Long help text goes here

Options:

(Use --verbose to get a full option listing)
''')
        self.assertRaises(SystemExit, self.captureOutput,
                          cmd.runCommand, None, {}, 
                          ['rbuild', 'help', 'bam'])

    def testInvalidSubCommandHelp(self):
        mainHandler = main.RbuildMain()
        mainHandler.registerCommand(FooSubCommand)
        cmd = helpcommand.HelpCommand()
        cmd.setMainHandler(mainHandler)

        self.assertRaises(SystemExit, self.captureOutput,
                          cmd.runCommand, None, {}, 
                          ['rbuild', 'help', 'foo', 'bam'])

    def testNoSubCommandHelp(self):
        '''
        Regression test for APPENG-2736
        '''
        mainHandler = main.RbuildMain()
        mainHandler.registerCommand(FooCommand)
        cmd = helpcommand.HelpCommand()
        cmd.setMainHandler(mainHandler)

        rc, txt = self.captureOutput(cmd.runCommand, None, {}, 
                                     ['rbuild', 'help', 'foo', 'bar'])
        self.assertEquals(rc, 0)
        txt = txt.replace('usage', 'Usage')  # difference between 2.4/2.5
        txt = txt.replace('options', 'Options')  # difference between 2.4/2.5
        assert(txt == '''\
Usage: rbuild foo 

Long help text goes here

Options:

(Use --verbose to get a full option listing)
''')
