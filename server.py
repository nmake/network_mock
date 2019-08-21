#!/usr/bin/env python
""" start the server
"""
import concurrent.futures
import logging
import argparse
import sys
import traceback
from network_server import NetworkServer


def _spawn(*args, **kwargs):
    while True:
        try:
            NetworkServer(*args, **kwargs).run()
        except ModuleNotFoundError as exc:
            LOGGER.error(
                "Requirements not satisfied for enabled plugins. Please see docuemention."
            )

            LOGGER.error(exc)
            sys.exit(1)
        except Exception as exc:  # pylint: disable=W0703
            if str(exc) in ["Socket is closed"]:
                LOGGER.warning(exc)
            else:
                traceback.print_exc()


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


def main():
    """ main
    """
    args = _parse_args()
    executor = concurrent.futures.ProcessPoolExecutor(args.server_count)
    futures = [
        executor.submit(
            _spawn,
            host_key_path=args.ssh_key,
            port=args.base_port + item,
            directory=args.directory,
            password=args.password,
            username=args.username,
            plugins=args.enable_plugins,
        )
        for item in range(0, args.server_count)
    ]
    for future in concurrent.futures.as_completed(futures):
        future.result()


if __name__ == "__main__":
    LOGGER = logging.getLogger()
    logging.basicConfig(level=logging.INFO)
    main()
