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

BASE_PORT = 2200
SERVER_COUNT = 10
CONFIG_DIR = "./configs"


class Server(paramiko.ServerInterface):
    """ paramiko server
    """

    def __init__(self):
        self.event = threading.Event()

    def check_channel_request(self, kind, chanid):
        return paramiko.OPEN_SUCCEEDED

    def check_auth_password(self, username, password):
        return paramiko.AUTH_SUCCESSFUL

    def get_allowed_auths(self, username):
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
    def __init__(self, host_key_path, port):
        self._history = []
        self._host_key_path = host_key_path
        self._channel = None
        self._conf_mode = False
        self._port = port
        self._session_meta = {}
        self._transport = None
        self._prompt = "router#"

    def run(self):
        host_key = paramiko.RSAKey(filename=self._host_key_path)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", self._port))
        logging.info("SSH server bound to port %s", self._port)
        sock.listen(100)
        client, addr = sock.accept()
        logging.info("Connection from %s on port %s", addr, self._port)
        self._transport = paramiko.Transport(client)
        self._transport.load_server_moduli()
        self._transport.add_server_key(host_key)
        server = Server()
        self._transport.start_server(server=server)
        self._channel = self._transport.accept(20)
        if self._channel is None:
            sys.exit(1)
        self._interactive()

    def _is_conf(self, line):
        confcmd = re.match(
            r"(?P<conf>conf)(igure)?( (?P<conf_mode>.*))?", line
        )
        if confcmd:
            cap = confcmd.groupdict()
            logger.info(
                "user entered configure mode with %s",
                cap.get("conf_mode", "none"),
            )
            self._conf_mode = True
            return True
        return False

    def _is_exit(self, line):
        if line == "exit":
            if self._conf_mode:
                logger.info("user exited configure mode")
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
            self._channel.send(
                "\r\n{:<20}{:<50}".format("#hostname=xxx", "Set the hostname")
            )
            self._channel.send(
                "\r\n{:<20}{:<50}".format("!hostname=xxx", "Set the hostname")
            )
            if "hostname" in self._session_meta:
                hostdir = "{}/{}".format(
                    CONFIG_DIR, self._session_meta["hostname"]
                )
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

    def _is_meta(self, line):
        metacmd = re.match(r"[#!](?P<key>.*)=(?P<value>.*)", line)
        if metacmd:
            cap = metacmd.groupdict()
            self._session_meta[cap["key"]] = cap["value"]
            if cap["key"] == "hostname":
                self._prompt = cap["value"] + "#"
            return True
        return False

    def _is_show(self, line):
        showcmd = re.match(r"show (?P<value>.*)", line)
        if showcmd:
            cap = showcmd.groupdict()
            if "hostname" not in self._session_meta:
                if cap["value"] == "privilege":
                    self._channel.send("\n15")
                elif cap["value"] in ["version", "inventory"]:
                    pass
                else:
                    self._channel.send(
                        "\r\n% hostname must be set with a "
                        ' "#hostname=xxxx" or "!hostname=xxxx" command'
                    )
            else:
                self._get_and_send(line)
            return True
        return False

    def _get_and_send(self, line):
        try:
            with open(
                "{}/{}/{}.txt".format(
                    CONFIG_DIR, self._session_meta["hostname"], line
                ),
                "r",
            ) as fhand:
                content = fhand.read()
            content = "\r\n".join(content.splitlines())
            self._channel.send(content)
        except FileNotFoundError:
            self._channel.send('% command file missing for "{}"'.format(line))

    def _handle_command(self, line):
        if self._is_exit(line):
            return
        if self._is_help(line):
            return
        if self._is_history(line):
            return
        if self._is_conf(line):
            return
        if self._is_meta(line):
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
                self._channel.send("\b \b")
                line_buffer = line_buffer[0:-1]
            elif char not in [b"\r", b"\n"]:
                line_buffer.append(char.decode("utf-8"))
            else:
                line = "".join(line_buffer)
                self._history.append(line)
                line_buffer = []
                logger.info(
                    "%s: %s",
                    self._session_meta.get("hostname", "unknown"),
                    line,
                )
                self._handle_command(line)
                self._channel.send("\r\n{}".format(self._prompt))


def _spawn(host_key_path, port):
    while True:
        try:
            NetworkServer(host_key_path, port).run()
        except Exception as exc:  # pylint: disable=W0703
            logger.warning(exc)


def main():
    """ main
    """
    if len(sys.argv) != 2:
        print("Need private host RSA key as argument.")
        sys.exit(1)

    host_key_path = sys.argv[1]
    executor = concurrent.futures.ProcessPoolExecutor(SERVER_COUNT)
    futures = [
        executor.submit(_spawn, host_key_path, BASE_PORT + item)
        for item in range(0, SERVER_COUNT)
    ]
    for future in concurrent.futures.as_completed(futures):
        future.result()


if __name__ == "__main__":
    logger = logging.getLogger()
    logging.basicConfig(level=logging.INFO)
    main()
