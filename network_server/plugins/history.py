""" A plugin for handling help and ?
"""
import re
from network_server.plugins import PluginBase


class History(PluginBase):
    """ history
    """

    PLUGIN_HELP = "Show the command history."

    def __init__(self, *args, **kwargs):
        super(History, self).__init__(*args, **kwargs)
        self._history = None

    def commands(self):
        return ["history", re.compile(r"!\d+")]

    # pylint: disable=W0212
    async def execute_command(self, line):
        self._logger.info("%s: %s", self._hostname, line)
        if line == "history":
            self._history = self._process.channel._editor._history
            rjust_amt = len(str(len(self._history))) + 1
            formatted_history = [
                "{}  {}".format(str(idx).rjust(rjust_amt), cmd)
                for idx, cmd in enumerate(self._history)
            ]
            output = "\r\n".join(formatted_history) + "\r\n"
            return self.respond(output=output)
        if re.match(r"!(?P<hnum>\d+)", line):
            command = re.match(r"!(?P<hnum>\d+)", line)
            cap = command.groupdict()
            try:
                history_command = self._history[int(cap["hnum"])]
                self._process.channel._editor._line = history_command
                self._process.channel._editor._update_input(
                    0, len(self._process.channel._editor._line)
                )
            except IndexError:
                self._process.channel._editor._ring_bell()
        return self.respond()
