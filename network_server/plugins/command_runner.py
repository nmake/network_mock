""" cmdrunner
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
import re
import uuid

import ansible_runner
from network_server.plugins import PluginBase

CHECK = "\u2714"  # heavy checkmark
XMARK = "\u2716"  # heavy multiplication
MINUS = "\u2796"  # heavy minus


class CommandRunner(PluginBase):
    def __init__(self, *args, **kwargs):
        super(CommandRunner, self).__init__(*args, **kwargs)
        self._in_context = False
        self._meta = {}

    def commands(self):
        return ["cmdrunner"]

    def _default_commands(self):
        if self._meta["os"] == "ios":
            return ["show running-config"]
        if self._meta["os"] == "nxos":
            return [
                "show privilege",
                "show inventory",
                "show version",
                "show running-config",
            ]
        if self._meta["os"] == "eos":
            return [
                "show version | json",
                "show hostname | json",
                "show running-config",
            ]
        if self._meta["os"] == "vyos":
            return ["show config", "show configuration commands"]
        return []

    async def _handle_command(self, line):
        line = line.rstrip()
        match = re.match(r"^set (?P<meta>.*)=(?P<value>.*)$", line)
        if match:
            cap = match.groupdict()
            self._meta[cap["meta"]] = cap["value"]
        elif line == "run":
            await self._run()
        return

    def _event_handler(self, event):
        host = event["event_data"]["host"]
        event_status = event["event"].split("_")[-1]
        if event_status == "ok":
            self.send_status(
                u"[{}] [{}] ran '{}'\n".format(CHECK, host, event["command"])
            )

        elif event_status == "failed":
            self.send_status(
                u"[{}] [{}] error '{}' '{}'\n".format(
                    XMARK,
                    host,
                    event["command"],
                    event["event_data"]["res"]["msg"],
                )
            )

    async def _run(self):
        failed = False
        if "password" not in self._meta:
            self.send_status("Password must be set 'set password=xxxx'\n")
            failed = True

        if "os" not in self._meta:
            self.send_status(
                "The OS must be set to a valid ansible network os"
                " 'set os=nxos'\n"
            )
            failed = True
        if failed:
            return
        if "commands" in self._meta:
            commands = [
                command.strip()
                for command in self._meta["commands"].split(",")
            ]
        else:
            commands = self._default_commands()
        acr = AnsibleCommandsRunner(
            commands=commands,
            hosts=list(self._hosts().keys()),
            inventory=self._inventory(),
            event_handler=self._event_handler,
        )
        self.send_status("Running...\n")
        results = await acr.run()

        for host, commands in results.items():
            directory = "{}/{}".format(self._directory, host)
            if not os.path.exists(directory):
                os.makedirs(directory)
            for command, result in commands.items():
                filename = "{}/{}.txt".format(directory, command)
                with open(filename, "w") as out_file:
                    out_file.write(result["stdout"])
                    self.send_status(
                        "[{}] [{}] wrote '{}'\n".format(CHECK, host, filename)
                    )

        return

    def _hosts(self):
        if "hosts" in self._meta:
            return {host: {} for host in self._meta["hosts"].split(",")}
        return {self._hostname: {}}

    def _inventory(self):
        username = self._meta.get("username") or self.username
        password = self._meta.get("become_pass") or self._meta["password"]
        inventory = {
            "all": {
                "hosts": self._hosts(),
                "vars": {
                    "ansible_user": username,
                    "ansible_password": self._meta["password"],
                    "ansible_become_pass": password,
                    "ansible_become": self._meta.get("become") is None,
                    "ansible_become_method": "enable",
                    "ansible_connection": "network_cli",
                    "ansible_network_os": self._meta["os"],
                },
            }
        }
        return inventory

    async def execute_command(self, line):
        if not self._in_context:
            self._logger.info(
                "%s: User entered cmdrunner mode", self._hostname
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
            await self._handle_command(line)
            return self.respond(context=self)

        return self.respond(context=self, new_prompt="cmdrunner>")


class AnsibleCommandsRunner:  # pylint: disable=R0903
    """ run commands using runner and cli_command
    """

    DESIRED_EVENTS = ["runner_on_ok", "runner_on_failed", "runner_on_skipped"]

    def __init__(self, commands, hosts, inventory, event_handler):
        self._commands = commands
        self._hosts = hosts
        self._inventory = inventory
        self._event_handler = event_handler
        self._events = []
        self._tasks = []

    def _interesting_event(self, event):
        if event["event"] in self.DESIRED_EVENTS:
            task_name = event.get("event_data", {}).get("task")
            event["command"] = next(
                task["cli_command"]["command"]
                for task in self._tasks
                if task["name"] == task_name
            )
            self._event_handler(event)
        if event["event"] == "runner_on_ok":
            self._events.append(event)

    async def run(self):
        """ run
        """
        self._tasks = [
            {"name": str(uuid.uuid1()), "cli_command": {"command": command}}
            for command in self._commands
        ]
        playbook = [
            {"hosts": self._hosts, "gather_facts": False, "tasks": self._tasks}
        ]
        executor = ThreadPoolExecutor(max_workers=1)
        loop = asyncio.get_event_loop()

        await loop.run_in_executor(
            executor,
            lambda: ansible_runner.run(
                playbook=playbook,
                inventory=self._inventory,
                json_mode=True,
                quiet=True,
                event_handler=self._interesting_event,
            ),
        )
        results_by_host = {}

        for host in self._hosts:
            results_by_host[host] = {}
            for task in playbook[0]["tasks"]:
                res = [
                    {
                        "event": event["event"],
                        "stdout": event["event_data"]["res"].get("stdout"),
                        "message": event["event_data"]["res"].get("msg"),
                    }
                    for event in self._events
                    if event.get("event_data", {}).get("task") == task["name"]
                    and event["event_data"]["host"] == host
                ]
                if res:
                    results_by_host[host][
                        task["cli_command"]["command"]
                    ] = res[0]
        return results_by_host
