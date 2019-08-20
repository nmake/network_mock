""" A plugin for handling help and ?
"""
import logging
from typing import Pattern
from network_server.plugins import PluginBase


class Help(PluginBase):
    def __init__(self, *args, **kwargs):
        super(Help, self).__init__(*args, **kwargs)
        self._logger = logging.getLogger(self.__class__.__name__)
        logging.basicConfig(level=logging.INFO)

    def commands(self):
        return ["help"]

    def keystrokes(self):
        return [b"?"]

    def execute_command(self, line):
        self._logger.info("%s: %s", self._hostname, line)
        output = "\r\n\r\nGENERAL COMMANDS"
        output += "\r\n{:<20}{:<50}".format("exit", "Exit the session")
        output += "\r\n{:<20}{:<50}".format("help", "Get help")
        output += "\r\n{:<20}{:<50}".format("!x", "Run cmd from history")
        output += "\r\n\r\nOTHER AVAILABLE COMMANDS"
        output += (
            "\r\n"
            + "\r\n".join(
                sorted(
                    [
                        key
                        for key in self._commands.keys()
                        if not isinstance(key, Pattern)
                    ]
                )
            )
            + "\r\n"
        )
        return self.respond(output=output)

    def execute_keystroke(self, *args, **kwargs):
        return self.execute_command("")
