""" the base paramiko server
"""
import threading
import logging
import paramiko


class ParamikoServer(paramiko.ServerInterface):
    """ paramiko server
    """

    def __init__(self, username, password):
        self.event = threading.Event()
        self.hostname = None
        self._logger = logging.getLogger(self.__class__.__name__)
        logging.basicConfig(level=logging.INFO)
        self._valid_username = username
        self._valid_password = password
        self._username = None
        self.platform = None

    def check_channel_request(self, _kind, _chanid):
        return paramiko.OPEN_SUCCEEDED

    def check_auth_password(self, username, password):

        parts = username.split("::")
        self._username = parts[0]
        self.hostname = parts[1]
        self._logger.info("Hostname set to %s", self.hostname)

        if self._valid_password and password != self._valid_password:
            return paramiko.AUTH_FAILED
        if self._valid_username and self._username != self._valid_username:
            return paramiko.AUTH_FAILED
        return paramiko.AUTH_SUCCESSFUL

    def get_allowed_auths(self, username):
        parts = username.split("::")
        if len(parts) != 2:
            self._logger.warning("A 2 tuple username was not provided")
            return "Please use a username in the username::hostname format"
        return "password"

    def check_channel_pty_request(
        self, channel, term, width, height, pixelwidth, pixelheight, modes
    ):
        return True

    def check_channel_shell_request(self, channel):
        return True

    def check_channel_subsystem_request(self, channel, name):
        return True

    def check_channel_exec_request(self, channel, command):
        self.event.set()
        return True

    def get_banner(self):
        return ("", "")
