""" A plugin for handling help and ?
"""
from typing import Pattern
from network_server.plugins import PluginBase


class Help(PluginBase):
    """ Help
    """

    PLUGIN_HELP = "Show the help."

    def commands(self):
        return ["help"]

    def keystrokes(self):
        return [b"?"]

    async def execute_command(self, line):
        self._logger.info("%s: %s", self._hostname, line)
        output = "\nGENERAL COMMANDS"
        output += "\n{:<20}{:<50}".format("exit", "Exit the session")
        output += "\n{:<20}{:<50}".format("help", "Get help")
        output += "\n{:<20}{:<50}".format("!x", "Run cmd from history")
        output += "\n\nOTHER AVAILABLE COMMANDS"
        output += (
            "\n"
            + "\n".join(
                sorted(
                    [
                        "{:<20}{:<50}".format(
                            key, plugin["plugin"].PLUGIN_HELP
                        )
                        for key, plugin in self._commands.items()
                        if not isinstance(key, Pattern)
                    ]
                )
            )
            + "\n"
        )
        return self.respond(output=output)

    def execute_keystroke(self, *args, **kwargs):
        return self.execute_command("")
