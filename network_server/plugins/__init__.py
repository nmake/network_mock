""" the plugin base class
"""
import logging


class PluginBase:
    """ pluginbase
    """

    def __init__(self, *args, **kwargs):
        self._process = kwargs["process"]
        self._commands = kwargs["commands"]
        self._directory = kwargs["directory"]
        self._hostname = kwargs["hostname"]
        self.username = kwargs["username"]
        self._logger = logging.getLogger(self.__class__.__name__)
        logging.basicConfig(level=logging.INFO)

    def commands(self):
        return []

    def keystrokes(self):
        return []

    def execute_command(self, line):
        return "\r\n", True

    def execute_keystroke(self, char, line_buffer):
        return "", False

    def send_status(self, status):
        self._process.stdout.write(status)

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
