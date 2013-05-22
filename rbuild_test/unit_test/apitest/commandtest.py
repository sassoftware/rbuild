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

from conary.lib import log

from rbuild.pluginapi import command
from rbuild.internal import main
from rbuild.internal import helpcommand


class BaseCommandTest(rbuildhelp.RbuildHelper):
    def testAddParameters(self):
        cmd = command.BaseCommand()
        d = {}
        cmd.addParameters(d)
        self.assertEquals(set(d['Common Options']),
            set(['config', 'config-file', 'lsprof', 'quiet', 
            'skip-default-config', 'stage', 'verbose']))

    def testProcessConfigOptions(self):
        configPath = self.rootDir + '/rbuildrc'
        self.writeFile(configPath, 'user newuser\n')
        cmd = command.BaseCommand()
        cmd.processConfigOptions(self.rbuildCfg, {},
                                 {'config-file' : [configPath],
                                  'verbose' : True })
        self.assertEquals(self.rbuildCfg.user, ('newuser', None))
        self.assertEquals(log.getVerbosity(), log.DEBUG)

    def testRunCommand(self):
        cmd = command.BaseCommand()
        self.assertRaises(NotImplementedError,
                          cmd.runCommand, None, None, None)


class CommandWithSubCommands(rbuildhelp.RbuildHelper):
    def genCommand(self):
        class MyCommand(command.CommandWithSubCommands):
            """My command usage"""
            commands = ['main']
        return MyCommand

    def genCommand2(self):
        class MyCommand(command.CommandWithSubCommands):
            commands = ['main']
        return MyCommand

    def genSubCommand(self):
        class SubCommand(command.BaseCommand):
            """general documentation about sub command"""
            paramHelp = 'option1 option2'
            help = 'executes subcommand'
            command = ['sub']
            def runCommand(self, handle, argSet, args):
                if len(args) > 3:
                    return self.usage()
                print args
                return 0

        return SubCommand

    def testRegisterCommand(self):
        baseCommand = self.genCommand()
        subCommand = self.genSubCommand()
        cmd = baseCommand()
        mainHandler = main.RbuildMain()
        mainHandler._registerCommand(baseCommand)
        cmd.setMainHandler(mainHandler)
        rc, txt = self.captureOutput(cmd.runCommand, None, {},
                                     ['main', 'sub', 'arg'])
        self.assertEquals(txt, '''%(usage)s: rbuild main <subcommand> [options]

My command usage

Subcommands:

(Use 'rbuild help main <subcommand>' for help on a subcommand)

%(options)s:

(Use --verbose to get a full option listing)
''' % self.optparseDifferences)
        assert(rc == 1)
        baseCommand.registerSubCommand('sub', subCommand)
        assert(baseCommand.getSubCommandClass('sub') == subCommand)
        assert(baseCommand.getSubCommandClass('unknownsub') == None)
        cmd = baseCommand()
        cmd.setMainHandler(mainHandler)
        rc, txt = self.captureOutput(cmd.runCommand, None, {},
                                     ['main'])
        mainCommandUsage = '''\
%(usage)s: rbuild main <subcommand> [options]

My command usage

Subcommands:
     sub  executes subcommand

(Use 'rbuild help main <subcommand>' for help on a subcommand)

%(options)s:

(Use --verbose to get a full option listing)
''' % self.optparseDifferences
        self.assertEquals(txt, mainCommandUsage)
        assert(rc == 1)
        rc, txt = self.captureOutput(cmd.runCommand, None, {},
                                     ['main', 'unknownsub'])
        assert(rc == 1)
        self.assertEquals(txt, mainCommandUsage)
        rc, txt = self.captureOutput(cmd.runCommand, None, {},
                                     ['main', 'unknownsub', 'unknownsubsub'])
        assert(rc == 1)
        self.assertEquals(txt, mainCommandUsage)
        rc, txt = self.captureOutput(
            cmd.runCommand, None, {}, ['rbuild', 'main', 'sub', 'arg'])
        self.assertEquals(rc, 0)
        self.assertEquals(txt, "['main', 'sub', 'arg']\n")

        cmd.setMainHandler(mainHandler)
        rc, txt = self.captureOutput(
            cmd.runCommand, None, {}, ['rbuild', 'main', 'sub', 'arg', 'arg2'])
        self.assertEquals(rc, 1)
        subCommandUsage = '''\
%(usage)s: rbuild main sub option1 option2

general documentation about sub command

%(options)s:

(Use --verbose to get a full option listing)
''' % self.optparseDifferences
        self.assertEquals(txt, subCommandUsage)

        helpCommand = helpcommand.HelpCommand()
        helpCommand.setMainHandler(mainHandler)
        rc, txt = self.captureOutput(
            helpCommand.runCommand, None, {}, ['rbuild', 'help', 'main', 'sub'])
        self.assertEquals(txt, subCommandUsage)

        rc, txt = self.captureOutput(
            helpCommand.runCommand, None, {}, ['rbuild', 'help', 'main'])
        self.assertEquals(txt, mainCommandUsage)

    def testCommandWithNoDocs(self):
        baseCommand = self.genCommand2()
        subCommand = self.genSubCommand()
        cmd = baseCommand()
        mainHandler = main.RbuildMain()
        mainHandler._registerCommand(baseCommand)
        cmd.setMainHandler(mainHandler)
        baseCommand.registerSubCommand('sub', subCommand)
        _, txt = self.captureOutput(cmd.runCommand, None, {},
                                     ['main'])
        self.assertEquals(txt, '''\
%(usage)s: rbuild main <subcommand> [options]



Subcommands:
     sub  executes subcommand

(Use 'rbuild help main <subcommand>' for help on a subcommand)

%(options)s:

(Use --verbose to get a full option listing)
''' % self.optparseDifferences)

    def testSubCommandWithAilas(self):
        baseCommand = self.genCommand()
        subCommand = self.genSubCommand()
        mainHandler = main.RbuildMain()
        mainHandler._registerCommand(baseCommand)
        baseCommand.registerSubCommand('sub', subCommand, aliases=['sub2', ])
        assert(baseCommand.getSubCommandClass('sub') == subCommand)
        assert(baseCommand.getSubCommandClass('sub2') == subCommand)
        assert(baseCommand.getSubCommandClass('unknownsub') == None)
        cmd = baseCommand()
        cmd.setMainHandler(mainHandler)
        rc, txt = self.captureOutput(cmd.runCommand, None, {},
                                     ['main'])
        mainCommandUsage = '''\
%(usage)s: rbuild main <subcommand> [options]

My command usage

Subcommands:
     sub  executes subcommand

(Use 'rbuild help main <subcommand>' for help on a subcommand)

%(options)s:

(Use --verbose to get a full option listing)
''' % self.optparseDifferences
        self.assertEquals(txt, mainCommandUsage)
        assert(rc == 1)

        subCommandUsage = '''\
%(usage)s: rbuild main sub option1 option2

general documentation about sub command

%(options)s:

(Use --verbose to get a full option listing)
''' % self.optparseDifferences

        cmd.setMainHandler(mainHandler)
        rc, txt = self.captureOutput(
            cmd.runCommand, None, {}, ['rbuild', 'main', 'sub', 'arg', 'arg2'])
        self.assertEquals(rc, 1)
        self.assertEquals(txt, subCommandUsage)

        rc, txt = self.captureOutput(
            cmd.runCommand, None, {}, ['rbuild', 'main', 'sub2', 'arg', 'arg2'])
        self.assertEquals(rc, 1)
        self.assertEquals(txt, subCommandUsage)

        helpCommand = helpcommand.HelpCommand()
        helpCommand.setMainHandler(mainHandler)
        rc, txt = self.captureOutput(
            helpCommand.runCommand, None, {}, ['rbuild', 'help', 'main', 'sub'])
        self.assertEquals(txt, subCommandUsage)

        subCommandUsage2 = '''\
%(usage)s: rbuild main sub2 option1 option2

general documentation about sub command

%(options)s:

(Use --verbose to get a full option listing)
''' % self.optparseDifferences

        rc, txt = self.captureOutput(
            helpCommand.runCommand, None, {}, ['rbuild', 'help', 'main', 'sub2'])
        self.assertEquals(txt, subCommandUsage2)

        rc, txt = self.captureOutput(
            helpCommand.runCommand, None, {}, ['rbuild', 'help', 'main'])
        self.assertEquals(txt, mainCommandUsage)

