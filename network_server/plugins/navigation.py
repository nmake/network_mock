""" A plugin for handling navigation
"""
from network_server.plugins import PluginBase


class Navigation(PluginBase):
    def __init__(self, *args, **kwargs):
        super(Navigation, self).__init__(*args, **kwargs)

    def keystrokes(self):
        return [b"\x7f"]

    def execute_keystroke(self, char, line_buffer):
        print(char, line_buffer)
        if char == b"\x7f":
            if line_buffer:
                return "\b \b", False
        return None, False
