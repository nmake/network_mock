""" A plugin for handling navigation
"""
from network_server.plugins import PluginBase


class Navigation(PluginBase):
    def __init__(self, *args, **kwargs):
        super(Navigation, self).__init__(*args, **kwargs)

    def keystrokes(self):
        return [b"\x7f"]

    def execute_keystroke(self, char, line_buffer):
        if char == b"\x7f":
            if line_buffer:
                return self.respond(output="\b \b", prompt=False)
        return self.respond(output=None, prompt=False)
