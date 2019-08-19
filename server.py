#!/usr/bin/env python
import socket
import sys
import threading
import re
import concurrent.futures
import paramiko
import logging
from os import listdir
from os.path import isfile, join, splitext
import argparse


class Server(paramiko.ServerInterface):
    """ paramiko server
    """

    def __init__(self, username, password):
        self.event = threading.Event()
        self.hostname = None
        self._logger = logging.getLogger(self.__class__.__name__)
        logging.basicConfig(level=logging.INFO)
        self._valid_username = username
        self._valid_password = password
        self._username = None
        self.platform = None

    def check_channel_request(self, kind, chanid):
        return paramiko.OPEN_SUCCEEDED

    def check_auth_password(self, username, password):

        parts = username.split("::")
        self._username = parts[0]
        self.hostname = parts[1]
        self._logger.info("Hostname set to %s", self.hostname)

        if self._valid_password and password != self._valid_password:
            return paramiko.AUTH_FAILED
        if self._valid_username and self._username != self._valid_username:
            return paramiko.AUTH_FAILED
        return paramiko.AUTH_SUCCESSFUL

    def get_allowed_auths(self, username):
        parts = username.split("::")
        if len(parts) != 2:
            self._logger.warning("A 2 tuple username was not provided")
            return "Please use a username in the username::hostname format"
        return "password"

    def check_channel_pty_request(
        self, channel, term, width, height, pixelwidth, pixelheight, modes
    ):
        return True

    def check_channel_shell_request(self, channel):
        return True

    def check_channel_subsystem_request(self, channel, name):
        return True

    def check_channel_exec_request(self, channel, command):
        self.event.set()
        return True

    def get_banner(self):
        return ("", "")


class NetworkServer:
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

    def run(self):
        host_key = paramiko.RSAKey(filename=self._host_key_path)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("", self._port))
        except Exception as e:
            self.logger.error("Bind failed: " + str(e))
            sys.exit(1)
        self._logger.info("SSH server bound to port %s", self._port)
        sock.listen(100)
        client, addr = sock.accept()
        self._logger.info("Connection from %s on port %s", addr, self._port)
        self._transport = paramiko.Transport(client)
        self._transport.load_server_moduli()
        self._transport.add_server_key(host_key)
        server = Server(password=self._password, username=self._username)
        self._transport.start_server(server=server)
        self._channel = self._transport.accept(20)
        if self._channel is None:
            sys.exit(1)
        self._hostname = server.hostname
        self._prompt = server.hostname + "#"
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

    def _is_help(self, line):
        command = re.match(r"(\?|help)", line)
        if command:
            self._channel.send("\r\n\r\nGENERAL COMMANDS")
            self._channel.send(
                "\r\n{:<20}{:<50}".format("exit", "Exit the session")
            )
            self._channel.send("\r\n{:<20}{:<50}".format("help", "Get help"))
            self._channel.send(
                "\r\n{:<20}{:<50}".format("history", "Show history")
            )
            self._channel.send(
                "\r\n{:<20}{:<50}".format("!x", "Run cmd from history")
            )
            hostdir = "{}/{}".format(self._directory, self._hostname)
            files = [
                splitext(f)[0]
                for f in listdir(hostdir)
                if isfile(join(hostdir, f))
            ]
            self._channel.send("\r\n\r\nAVAILABLE NETWORK COMMANDS")
            self._channel.send("\r\n" + "\r\n".join(files) + "\r\n")
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

    def _is_show(self, line):
        showcmd = re.match(r"show (?P<value>.*)", line)
        if showcmd:
            self._get_and_send(line)
            return True
        return False

    def _get_and_send(self, line):
        try:
            with open(
                "{}/{}/{}.txt".format(self._directory, self._hostname, line),
                "r",
            ) as fhand:
                content = fhand.read()
            content = "\r\n".join(content.splitlines()) + "\r\n"
            self._channel.send(content)
        except FileNotFoundError:
            self._channel.send('% command file missing for "{}"'.format(line))

    def _handle_command(self, line):  # pylint: disable=R0911
        if self._is_exit(line):
            return
        if self._is_help(line):
            return
        if self._is_history(line):
            return
        if self._is_conf(line):
            return
        if self._is_show(line):
            return
        return

    def _interactive(self):
        fhandle = self._channel.makefile("rU")
        line_buffer = []
        self._channel.send("\r\n{}".format(self._prompt))
        while not self._channel.closed:
            char = fhandle.read(1)
            self._channel.send(char)
            if char in [b"\x7f"]:  # backspace
                if line_buffer:
                    self._channel.send("\b \b")
                    line_buffer = line_buffer[0:-1]
            elif char not in [b"\r", b"\n"]:
                line_buffer.append(char.decode("utf-8"))
            else:
                line = "".join(line_buffer)
                self._history.append(line)
                line_buffer = []
                self._logger.info("%s: %s", self._hostname, line)
                self._handle_command(line)
                self._channel.send("\r\n{}".format(self._prompt))


def _spawn(host_key_path, port, directory, password, username):
    while True:
        try:
            NetworkServer(
                host_key_path, port, directory, password, username
            ).run()
        except Exception as exc:  # pylint: disable=W0703
            LOGGER.warning(exc)


def _parse_args():
    """ Entrypoint
    """
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "-b",
        "--base-port",
        default=2200,
        type=int,
        help="Base port for the SSH server.",
    )

    parser.add_argument(
        "-d",
        "--directory",
        default="./examples/configs",
        help="The path to the device/commands directories.",
    )

    parser.add_argument(
        "-p",
        "--password",
        default=None,
        help="The SSH server authentication password.",
    )

    parser.add_argument(
        "-u", "--username", help="The SSH server authentication username."
    )

    parser.add_argument(
        "-c",
        "--server-count",
        default=10,
        type=int,
        help="The number of SSH servers to start.",
    )

    parser.add_argument(
        "-k", "--ssh_key", help="Server side SSH key file path", required=True
    )

    args = parser.parse_args()
    return args


def main():
    """ main
    """
    args = _parse_args()
    executor = concurrent.futures.ProcessPoolExecutor(args.server_count)
    futures = [
        executor.submit(
            _spawn,
            args.ssh_key,
            args.base_port + item,
            args.directory,
            args.password,
            args.username,
        )
        for item in range(0, args.server_count)
    ]
    for future in concurrent.futures.as_completed(futures):
        future.result()


if __name__ == "__main__":
    LOGGER = logging.getLogger()
    logging.basicConfig(level=logging.INFO)
    main()
