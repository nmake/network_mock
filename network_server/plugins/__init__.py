""" the plugin base class
"""


class PluginBase:
    """ pluginbase
    """

    def __init__(self, *args, **kwargs):
        self._commands = kwargs["commands"]
        self._directory = kwargs["directory"]
        self._history = kwargs["history"]
        self._hostname = kwargs["hostname"]

    def commands(self):
        return []

    def keystrokes(self):
        return []

    def execute_command(self, line):
        return "\r\n", True

    def execute_keystroke(self, *args, **kwargs):
        return "", False

    def respond(
        self,
        output="",
        issue_command="",
        prompt=True,
        context=False,
        new_prompt=False,
    ):
        return {
            "output": output,
            "issue_command": issue_command,
            "prompt": prompt,
            "context": context,
            "new_prompt": new_prompt,
        }
