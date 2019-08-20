""" A plugin for handling help and ?
"""
from network_server.plugins import PluginBase


class Help(PluginBase):
    def __init__(self, *args, **kwargs):
        super(Help, self).__init__(*args, **kwargs)

    def commands(self):
        return ["help"]

    def keystrokes(self):
        return [b"?"]

    def execute_command(self, *args, **kwargs):
        output = "\r\n\r\nGENERAL COMMANDS"
        output += "\r\n{:<20}{:<50}".format("exit", "Exit the session")
        output += "\r\n{:<20}{:<50}".format("help", "Get help")
        output += "\r\n{:<20}{:<50}".format("!x", "Run cmd from history")
        output += "\r\n\r\nOTHER AVAILABLE COMMANDS"
        output += "\r\n" + "\r\n".join(self._commands.keys()) + "\r\n"
        return output, True

    def execute_keystroke(self, *args, **kwargs):
        return self.execute_command("")
