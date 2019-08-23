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
        default=10,
        type=int,
        help="The number of SSH servers to start.",
    )

    parser.add_argument(
        "-k", "--ssh_key", help="Server side SSH key file path", required=True
    )

    args = parser.parse_args()
    return args


def _spawn(port, args):
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(start_server(port, **vars(args)))
    except (OSError, asyncssh.Error) as exc:
        sys.exit("Error starting server: " + str(exc))
    loop.run_forever()


def main():
    args = _parse_args()
    executor = concurrent.futures.ProcessPoolExecutor(args.server_count)
    futures = [
        executor.submit(_spawn, port=args.base_port + item, args=args)
        for item in range(0, args.server_count)
    ]
    for future in concurrent.futures.as_completed(futures):
        future.result()


if __name__ == "__main__":
    LOGGER = logging.getLogger()
    logging.basicConfig(level=logging.INFO)
    main()
