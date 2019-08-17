#!/usr/bin/env python
import socket
import sys
import threading
import re
import concurrent.futures
import paramiko
import logging

BASE_PORT = 3000
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


def run_server(transport):
    channel = transport.accept(20)
    if channel is None:
        sys.exit(1)

    prompt = "router#"
    meta = {}
    fhandle = channel.makefile("rU")

    channel.send("\r\n{}".format(prompt))
    while True:
        line = fhandle.readline().rstrip()
        logger.info("%s: %s", meta.get("hostname", "unknown"), line)
        metacmd = re.match(r"meta: (?P<key>.*)=(?P<value>.*)", line)
        if metacmd:
            cap = metacmd.groupdict()
            meta[cap["key"]] = cap["value"]
        showcmd = re.match(r"show (?P<value>.*)", line)
        if showcmd:
            cap = showcmd.groupdict()
            if cap["value"] == "privilege" and "hostname" not in meta:
                channel.send("\n15")
            elif (
                cap["value"] in ["version", "inventory"]
                and "hostname" not in meta
            ):
                pass
            elif "hostname" not in meta:
                channel.send(
                    '% hostname must be set with a "meta: hostname=xxxx" command'
                )
            else:
                try:
                    with open(
                        "{}/{}/{}.txt".format(
                            CONFIG_DIR, meta["hostname"], line
                        ),
                        "r",
                    ) as fhand:
                        content = fhand.read()
                    channel.send(content)
                except FileNotFoundError:
                    channel.send(
                        '% command file missing for "{}"'.format(line)
                    )
        channel.send("\r\n{}".format(prompt))


def listener(host_key_path, port):
    host_key = paramiko.RSAKey(filename=host_key_path)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", port))
    sock.listen(100)
    client, addr = sock.accept()
    logging.info("connection from %s", addr)
    transport = paramiko.Transport(client)
    transport.load_server_moduli()
    transport.add_server_key(host_key)
    server = Server()
    transport.start_server(server=server)
    run_server(transport)


def _spawn(host_key_path, port):
    while True:
        try:
            listener(host_key_path, port)
        except Exception:  # pylint: disable=W0703
            pass


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
