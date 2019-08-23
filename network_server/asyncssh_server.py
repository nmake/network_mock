import asyncssh
from network_server import ssh_session


async def start_server(*args, **kwargs):
    await asyncssh.create_server(
        lambda: SSHServer(**kwargs),
        "",
        args[0],
        server_host_keys=kwargs["ssh_key"],
        process_factory=ssh_session,
    )


class SSHServer(asyncssh.SSHServer):
    def __init__(self, *args, **kwargs):
        self._valid_username = kwargs["username"]
        self._valid_password = kwargs["password"]
        self._kwargs = kwargs

    def connection_made(self, conn):
        conn.set_extra_info(user_args=self._kwargs)

    @staticmethod
    def password_auth_supported():
        return True

    def validate_password(self, username, password):
        parts = username.split("::")
        if len(parts) == 2:
            username = parts[0]
        if self._valid_password and password != self._valid_password:
            return False
        if self._valid_username and username != self._valid_username:
            return False
        return True
