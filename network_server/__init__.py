""" the network server
"""
import logging
import re
import socket
import sys
import paramiko
from network_server.paramiko_server import ParamikoServer
from network_server.plugins.navigation import Navigation
from network_server.plugins.show_file_server import ShowFileServer
from network_server.plugins.help import Help


class NetworkServer:
    """ network_server
    """

    def __init__(self, host_key_path, port, directory, password, username):
        self._history = []
        self._host_key_path = host_key_path
        self._channel = None
        self._conf_mode = False
        self._directory = directory
        self._hostname = None
        self._logger = logging.getLogger(self.__class__.__name__)
        logging.basicConfig(level=logging.INFO)
        self._password = password
        self._port = port
        self._username = username
        self._transport = None
        self._prompt = "router#"
        self._commands = {}
        self._keystrokes = {}

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

    def _is_conf(self, line):
        confcmd = re.match(
            r"(?P<conf>conf)(igure)?( (?P<conf_mode>.*))?", line
        )
        if confcmd:
            self._logger.info(
                "%s: (user entered configure mode)", self._hostname
            )
            self._conf_mode = True
            return True
        return False

    def _is_exit(self, line):
        if line == "exit":
            if self._conf_mode:
                self._logger.info(
                    "%s: (user exited configure mode)", self._hostname
                )
                self._conf_mode = False
            else:
                self._transport.close()
            return True
        return False

    def _is_history(self, line):
        matched = False
        command = re.match(r"history", line)
        if command:
            matched = True
            formatted_history = [
                "{}  {}".format(str(idx).rjust(3), cmd)
                for idx, cmd in enumerate(self._history)
            ]
            self._channel.send("\r\n" + "\r\n".join(formatted_history))
        command = re.match(r"!(?P<hnum>\d+)", line)
        if command:
            matched = True
            cap = command.groupdict()
            try:
                history_command = self._history[int(cap["hnum"])]
                if not re.match(r"!(?P<hnum>\d+)", history_command):
                    self._channel.send("\r\n{}".format(history_command))
                    self._history.append(history_command)
                    self._handle_command(history_command)
            except IndexError:
                pass
        return matched

    def _handle_command(self, line):  # pylint: disable=R0911
        if line in self._commands:
            output, prompt = self._commands[line]["plugin"].execute_command(
                line
            )
            self._channel.send(output)
            if prompt:
                self._channel.send("\r\n{}".format(self._prompt))
            return
        if self._is_exit(line):
            return
        if self._is_history(line):
            self._channel.send("\r\n{}".format(self._prompt))
            return
        if self._is_conf(line):
            self._channel.send("\r\n{}".format(self._prompt))
            return
        self._channel.send("\r\n{}".format(self._prompt))
        return

    def _interactive(self):
        fhandle = self._channel.makefile("rU")
        line_buffer = []
        self._channel.send("\r\n{}".format(self._prompt))
        while not self._channel.closed:
            char = fhandle.read(1)
            self._channel.send(char)
            if char in self._keystrokes:
                output, prompt = self._keystrokes[char][
                    "plugin"
                ].execute_keystroke(char, line_buffer)
                self._channel.send(output or "")
                if prompt:
                    self._channel.send("\r\n{}".format(self._prompt))
                if line_buffer:
                    line_buffer = line_buffer[0:-1]

            elif char not in [b"\r", b"\n"]:
                line_buffer.append(char.decode("utf-8"))
            else:
                line = "".join(line_buffer)
                self._history.append(line)
                line_buffer = []
                self._logger.info("%s: %s", self._hostname, line)
                self._handle_command(line)

    def _load_plugins(self):
        plugins = [ShowFileServer, Help, Navigation]
        for plugin in plugins:
            plugin_initd = plugin(
                commands=self._commands,
                hostname=self._hostname,
                directory=self._directory,
            )
            commands = plugin_initd.commands()
            for command in commands:
                self._commands[command] = {"plugin": plugin_initd}
            keystrokes = plugin_initd.keystrokes()
            for keystroke in keystrokes:
                self._keystrokes[keystroke] = {"plugin": plugin_initd}
