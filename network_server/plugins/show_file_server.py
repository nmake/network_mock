""" A plugin for handling the show files
"""
import logging
from os.path import isfile, join, splitext
from os import listdir
from network_server.plugins import PluginBase


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
        with open(
            "{}/{}/{}.txt".format(self._directory, self._hostname, line), "r"
        ) as fhand:
            content = fhand.read()
        content = "\n" + "\n".join(content.splitlines()) + "\n"
        return self.respond(output=content)
