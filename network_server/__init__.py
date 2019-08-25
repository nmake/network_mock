import logging
import re
from typing import Pattern
import asyncssh

from network_server.plugins.show_file_server import ShowFileServer
from network_server.plugins.configure import Configure
from network_server.plugins.help import Help
from network_server.plugins.history import History

PLUGIN_REF = {
    "confmode": Configure,
    "showfs": ShowFileServer,
    "help": Help,
    "history": History,
}


async def ssh_session(process):
    """ kick off the ssh session and hand off
    """
    username = process.get_extra_info("username")
    if "::" in username:
        username, hostname = username.split("::")
    else:
        hostname = "mock"
    session = SSHSession(
        username, hostname, process, **process.get_extra_info("user_args")
    )
    while True:
        try:
            while True:
                res = await session.interactive()
                if not res:
                    process.exit(0)
        except asyncssh.BreakReceived:
            process.stdout.write("\r\n")
        except BrokenPipeError:
            process.connection_lost()


class SSHSession:  # pylint: disable=R0902, R0903
    """ ssh session
    """

    def __init__(self, *args, **kwargs):
        self._username = args[0]
        self._hostname = args[1]
        self._context = False
        self._directory = kwargs["directory"]
        self._plugins = kwargs["enable_plugins"]
        self._commands = {}
        self._keystrokes = {}
        self._process = args[2]
        self._prompt = self._hostname + "#"
        self._logger = logging.getLogger(self.__class__.__name__)
        if "cmdrunner" in self._plugins:
            from network_server.plugins.command_runner import CommandRunner

            PLUGIN_REF["cmdrunner"] = CommandRunner
        self._load_plugins()

    async def interactive(self):
        """ go interactive with the client
        """
        self._process.stdout.write("\r\n" + self._prompt)

        while True:
            user_input = await self._process.stdin.readline()
            if user_input == "":
                break
            res = await self._handle_command(user_input.rstrip())
            if not res:
                break

    async def _handle_command(self, line):  # pylint: disable=R0911
        # if in a context send all commands that way
        if self._context:
            response = await self._context.execute_command(line)
            await self._respond(response)
            return True
        # check for exact match
        if line in self._commands:
            response = await self._commands[line]["plugin"].execute_command(
                line
            )
            await self._respond(response)
            return True
        # check the regexs
        matches = [
            val
            for k, val in self._commands.items()
            if isinstance(k, Pattern) and re.match(k, line)
        ]
        if matches:
            response = await matches[0]["plugin"].execute_command(line)
            await self._respond(response)
            return True

        if line == "exit":
            return False

        self._logger.info("%s: No match for '%s'", self._hostname, line)
        await self._send_prompt()
        return True

    def _load_plugins(self):
        plugins = [val for k, val in PLUGIN_REF.items() if k in self._plugins]
        for plugin in plugins:
            plugin_initd = plugin(
                commands=self._commands,
                directory=self._directory,
                hostname=self._hostname,
                process=self._process,
                username=self._username,
            )
            commands = plugin_initd.commands()
            for command in commands:
                self._commands[command] = {"plugin": plugin_initd}
            self._logger.info("Enabled plugin: %s", plugin.__name__)

    async def _respond(self, response):
        self._process.stdout.write(response["output"])
        self._context = response["context"]
        if response["new_prompt"]:
            self._prompt = response["new_prompt"]
        if response["prompt"]:
            await self._send_prompt()

    async def _send_prompt(self):
        self._process.stdout.write(self._prompt)
