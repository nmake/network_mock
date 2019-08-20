""" A plugin for handling help and ?
"""
import re
from network_server.plugins import PluginBase


class History(PluginBase):
    """ history
    """

    def commands(self):
        return ["history", re.compile(r"!\d+")]

    def execute_command(self, *args, **kwargs):
        line = args[0]
        if line == "history":
            formatted_history = [
                "{}  {}".format(str(idx).rjust(3), cmd)
                for idx, cmd in enumerate(self._history)
            ]
            output = "\r\n" + "\r\n".join(formatted_history)
            return self.respond(output=output)
        if re.match(r"!(?P<hnum>\d+)", line):
            command = re.match(r"!(?P<hnum>\d+)", line)
            cap = command.groupdict()
            try:
                history_command = self._history[int(cap["hnum"])]
                if not re.match(r"!(?P<hnum>\d+)", history_command):
                    return self.respond(
                        output="\r\n" + history_command,
                        issue_command=history_command,
                    )
            except IndexError:
                pass
        return self.respond()
