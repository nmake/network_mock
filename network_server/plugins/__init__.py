""" the plugin base class
"""


class PluginBase:
    def __init__(self, *args, **kwargs):
        print(args, kwargs)
        self._commands = kwargs["commands"]
        self._directory = kwargs["directory"]
        self._hostname = kwargs["hostname"]

    def commands(self):
        return []

    def keystrokes(self):
        return []

    def execute_command(self, *args, **kwargs):
        return "\r\n", True

    def execute_keystroke(self, *args, **kwargs):
        return "", False
