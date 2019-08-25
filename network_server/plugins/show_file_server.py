""" A plugin for handling the show files
"""
import logging
from os.path import isfile, join, splitext
from os import listdir
from network_server.plugins import PluginBase
from concurrent.futures import ThreadPoolExecutor
import asyncio


class ShowFileServer(PluginBase):
    def __init__(self, *args, **kwargs):
        super(ShowFileServer, self).__init__(*args, **kwargs)

    def commands(self):
        hostdir = "{}/{}".format(self._directory, self._hostname)
        files = [
            splitext(f)[0]
            for f in listdir(hostdir)
            if isfile(join(hostdir, f))
        ]
        return files

    async def execute_command(self, line):
        self._logger.info("%s: %s", self._hostname, line)
        filename = "{}/{}/{}.txt".format(self._directory, self._hostname, line)
        executor = ThreadPoolExecutor(max_workers=1)
        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(
            executor, lambda: self._read_file(filename)
        )
        content = "\n" + "\n".join(content.splitlines()) + "\n"
        return self.respond(output=content)

    @staticmethod
    def _read_file(filename):
        with open(filename, "r") as fhand:
            return fhand.read()
