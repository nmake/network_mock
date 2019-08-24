import argparse
import logging
import asyncio
import sys
import asyncssh
from network_server.asyncssh_server import start_server
import concurrent.futures


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
        "-e",
        "--enable-plugins",
        type=lambda s: [item for item in s.split(",")],
        help="The plugins that should be enabled",
        default="confmode,showfs,help,history,navigation,showfs",
    )

    parser.add_argument(
        "-u", "--username", help="The SSH server authentication username."
    )

    parser.add_argument(
        "-c",
        "--server-count",
        default=1,
        type=int,
        help="The number of SSH servers to start.",
    )

    parser.add_argument(
        "-k", "--ssh_key", help="Server side SSH key file path", required=True
    )

    args = parser.parse_args()
    return args


def main():
    args = _parse_args()
    loop = asyncio.get_event_loop()
    for item in range(0, args.server_count):
        loop.create_task(start_server(args.base_port + item, **vars(args)))
    loop.run_forever()

if __name__ == "__main__":
    LOGGER = logging.getLogger()
    logging.basicConfig(level=logging.INFO)
    main()
