""" A plugin for the conf context
"""
import logging
import re
from network_server.plugins import PluginBase


class Configure(PluginBase):
    """ configuration mode
    """

    def __init__(self, *args, **kwargs):
        super(Configure, self).__init__(*args, **kwargs)
        self._logger = logging.getLogger(self.__class__.__name__)
        logging.basicConfig(level=logging.INFO)
        self._in_context = False

    def commands(self):
        return [re.compile("conf.*")]

    def execute_command(self, line):
        if not self._in_context:
            self._logger.info(
                "%s: User entered configure mode  with '%s'",
                self._hostname,
                line,
            )
            self._in_context = True
        elif line in ["exit", "end"]:
            self._in_context = False
            self._logger.info(
                "%s: User exited configure mode.", self._hostname
            )
            return self.respond(
                context=False, new_prompt="{}#".format(self._hostname)
            )
        else:
            self._logger.info("%s:%s", self._hostname, line)

        return self.respond(
            context=self, new_prompt="{}(configure)#".format(self._hostname)
        )
