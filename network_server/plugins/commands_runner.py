import ansible_runner
import uuid


class CommandsRunner:
    def __init__(self, commands, hosts, inventory):
        self._commands = commands
        self._hosts = hosts
        self._inventory = inventory

    def run(self):
        tasks = [
            {"name": str(uuid.uuid1()), "cli_command": {"command": command}}
            for command in self._commands
        ]
        playbook = [
            {"hosts": self._hosts, "gather_facts": False, "tasks": tasks}
        ]
        playbook_result = ansible_runner.run(
            playbook=playbook,
            inventory=self._inventory,
            json_mode=True,
            quiet=True,
        )
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
                    for task in playbook[0]["tasks"]
                ]
                if res:
                    results_by_host[host][
                        task["cli_command"]["command"]
                    ] = res[0]
        return results_by_host
