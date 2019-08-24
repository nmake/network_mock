import ansible_runner
import ansible
import os
import re
import uuid
from network_server.plugins import PluginBase
from concurrent.futures import ThreadPoolExecutor
import asyncio

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
        output = ""
        match = re.match(r"^set (?P<meta>.*)=(?P<value>.*)$", line)
        if match:
            cap = match.groupdict()
            self._meta[cap["meta"]] = cap["value"]
            output = ""
        elif line == "run":
            output = await self._run()
        return output

    async def _run(self):
        messages = []
        if "password" not in self._meta:
            messages.append("Password must be set 'set password=xxxx'")
        if "os" not in self._meta:
            messages.append(
                "The OS must be set to a valid ansible network os"
                " 'set os=nxos'"
            )
        if messages:
            return "\n" + "\n".join(messages) + "\n"
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
        )
        self.send_status("\r\nRunning commands on devices....")
        results = await acr.run()
        self.send_status("\r\nSaving command out into files....")

        messages = []
        for host, commands in results.items():
            directory = "{}/{}".format(self._directory, host)
            if not os.path.exists(directory):
                os.makedirs(directory)
            for command, result in commands.items():
                if result["event"] == "runner_on_ok":
                    filename = "{}/{}.txt".format(directory, command)
                    with open(filename, "w") as out_file:
                        out_file.write(result["stdout"])
                        messages.append(
                            "{}: wrote '{}'".format(host, filename)
                        )
                else:
                    messages.append(
                        "{}: '{}' returned an error".format(host, command)
                    )
        return "\n" + "\n".join(messages) + "\n"

    def _hosts(self):
        if "hosts" in self._meta:
            return {host: {} for host in self._meta["hosts"].split(",")}
        return {self._hostname: {}}

    def _inventory(self):
        inventory = {
            "all": {
                "hosts": self._hosts(),
                "vars": {
                    "ansible_user": self._meta.get("username")
                    or self.username,
                    "ansible_password": self._meta[
                        "password"
                    ],  # "{{ lookup('env', 'ansible_ssh_pass') }}",
                    "ansible_become_pass": self._meta.get("become_pass")
                    or self._meta["password"],
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
            output = await self._handle_command(line)
            return self.respond(context=self, output=output)

        return self.respond(context=self, new_prompt="cmdrunner>")


class AnsibleCommandsRunner:  # pylint: disable=R0903
    """ run commands using runner and cli_command
    """

    def __init__(self, commands, hosts, inventory):
        self._commands = commands
        self._hosts = hosts
        self._inventory = inventory

    async def run(self):
        """ run
        """
        tasks = [
            {"name": str(uuid.uuid1()), "cli_command": {"command": command}}
            for command in self._commands
        ]
        playbook = [
            {"hosts": self._hosts, "gather_facts": False, "tasks": tasks}
        ]
        executor = ThreadPoolExecutor(max_workers=3)
        loop = asyncio.get_event_loop()
        playbook_result = await loop.run_in_executor(executor,
                                                     lambda: ansible_runner.run
                                                     (playbook=playbook,
                                                     inventory=self._inventory,
                                                     json_mode=True,
                                                     quiet=True))
        results_by_host = {}
        desired_events = [
            "runner_on_ok",
            "runner_on_failed",
            "runner_on_skipped",
        ]
        for host in self._hosts:
            results_by_host[host] = {}
            for task in playbook[0]["tasks"]:
                res = [
                    {
                        "event": event["event"],
                        "stdout": event["event_data"]["res"].get("stdout"),
                    }
                    for event in list(playbook_result.events)
                    if event["event"] in desired_events
                    and event.get("event_data", {}).get("task") == task["name"]
                ]
                if res:
                    results_by_host[host][
                        task["cli_command"]["command"]
                    ] = res[0]
        return results_by_host
