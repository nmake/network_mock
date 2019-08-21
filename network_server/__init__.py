""" the network server
"""
import logging
import re
import socket
import sys
from typing import Pattern
import paramiko
from network_server.paramiko_server import ParamikoServer
from network_server.plugins.navigation import Navigation
from network_server.plugins.show_file_server import ShowFileServer
from network_server.plugins.configure import Configure
from network_server.plugins.help import Help
from network_server.plugins.history import History

PLUGIN_REF = {
    "confmode": Configure,
    "showfs": ShowFileServer,
    "help": Help,
    "history": History,
    "navigation": Navigation,
}


class NetworkServer:
    """ network_server
    """

    def __init__(
        self, host_key_path, port, directory, password, username, plugins
    ):
        self._history = []
        self._host_key_path = host_key_path
        self._channel = None
        self._context = False
        self._directory = directory
        self._hostname = None
        self._logger = logging.getLogger(self.__class__.__name__)
        logging.basicConfig(level=logging.INFO)
        self._password = password
        self._port = port
        self._plugins = plugins
        self._username = username
        self._transport = None
        self._prompt = "router#"
        self._commands = {}
        self._keystrokes = {}
        if "cmdrunner" in self._plugins:
            from network_server.plugins.command_runner import CommandRunner

            PLUGIN_REF["cmdrunner"] = CommandRunner

    def run(self):
        host_key = paramiko.RSAKey(filename=self._host_key_path)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("", self._port))
        except Exception as exc:  # pylint: disable=W0703
            self._logger.error("Bind failed: %s", str(exc))
            sys.exit(1)
        self._logger.info("SSH server bound to port %s", self._port)
        sock.listen(100)
        client, addr = sock.accept()
        self._logger.info("Connection from %s on port %s", addr, self._port)
        self._transport = paramiko.Transport(client)
        self._transport.load_server_moduli()
        self._transport.add_server_key(host_key)
        server = ParamikoServer(
            password=self._password, username=self._username
        )
        self._transport.start_server(server=server)
        self._channel = self._transport.accept(20)
        if self._channel is None:
            sys.exit(1)
        self._hostname = server.hostname
        self._prompt = server.hostname + "#"
        self._load_plugins()
        self._interactive()

    def _handle_command(self, line):  # pylint: disable=R0911
        self._history.append(line)
        # if in a context send all commands that way
        if self._context:
            response = self._context.execute_command(line)
            self._respond(response)
            return
        # check for exact match
        if line in self._commands:
            response = self._commands[line]["plugin"].execute_command(line)
            self._respond(response)
            return
        # check the regexs
        matches = [
            val
            for k, val in self._commands.items()
            if isinstance(k, Pattern) and re.match(k, line)
        ]
        if matches:
            response = matches[0]["plugin"].execute_command(line)
            self._respond(response)
            return

        if line == "exit":
            self._transport.close()
            return

        self._logger.info("%s: No match for '%s'", self._hostname, line)
        self._send_prompt()
        return

    def _interactive(self):
        fhandle = self._channel.makefile("rU")
        line_buffer = []
        self._send_prompt()
        while not self._channel.closed:
            char = fhandle.read(1)
            self._channel.send(char)
            if char in self._keystrokes:
                response = self._keystrokes[char]["plugin"].execute_keystroke(
                    char, line_buffer
                )
                self._channel.send(response["output"] or "")
                if response["prompt"]:
                    self._send_prompt()
                if line_buffer:
                    line_buffer = line_buffer[0:-1]

            elif char not in [b"\r", b"\n"]:
                line_buffer.append(char.decode("utf-8"))
            else:
                line = "".join(line_buffer)
                line_buffer = []
                self._handle_command(line)

    def _load_plugins(self):
        plugins = [val for k, val in PLUGIN_REF.items() if k in self._plugins]
        for plugin in plugins:
            plugin_initd = plugin(
                commands=self._commands,
                directory=self._directory,
                history=self._history,
                hostname=self._hostname,
                channel=self._channel,
                username=self._username,
            )
            commands = plugin_initd.commands()
            for command in commands:
                self._commands[command] = {"plugin": plugin_initd}
            keystrokes = plugin_initd.keystrokes()
            for keystroke in keystrokes:
                self._keystrokes[keystroke] = {"plugin": plugin_initd}
            self._logger.info("Enabled plugin: %s", plugin.__name__)

    def _respond(self, response):
        self._channel.send(response["output"])
        self._context = response["context"]
        if response["new_prompt"]:
            self._prompt = response["new_prompt"]
        if response["issue_command"]:
            self._handle_command(response["issue_command"])
        if response["prompt"]:
            self._send_prompt()

    def _send_prompt(self):
        self._channel.send("\r\n{}".format(self._prompt))
