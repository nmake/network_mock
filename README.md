# Network Mock

`network_mock` is a simple ssh server that can respond to network device `show` commands. It was authored as a debugging tool used during local development.

## Usage

```
usage: server.py [-h] [-b BASE_PORT] [-d DIRECTORY] [-p PASSWORD]
                 [-e ENABLE_PLUGINS] [-u USERNAME] [-c SERVER_COUNT] -k
                 SSH_KEY

optional arguments:
  -h, --help            show this help message and exit
  -b BASE_PORT, --base-port BASE_PORT
                        Base port for the SSH server. (default: 2200)
  -d DIRECTORY, --directory DIRECTORY
                        The path to the device/commands directories. (default:
                        ./examples/configs)
  -p PASSWORD, --password PASSWORD
                        The SSH server authentication password. (default:
                        None)
  -e ENABLE_PLUGINS, --enable-plugins ENABLE_PLUGINS
                        The plugins that should be enabled (default:
                        confmode,showfs,help,history,navigation,showfs)
  -u USERNAME, --username USERNAME
                        The SSH server authentication username. (default:
                        None)
  -c SERVER_COUNT, --server-count SERVER_COUNT
                        The number of SSH servers to start. (default: 1)
  -k SSH_KEY, --ssh_key SSH_KEY
                        Server side SSH key file path (default: None)

```

## Getting started

The previously retrieved command output needs to be stored in a directory, one per device. The file needs to be named as the exact command.

```
├── eos101
│   └── show run.txt
├── ios101
│   └── show run.txt
├── nxos101
│   └── show run.txt
└── vyos101
    └── show config.txt
```

## Starting the server

Update the server.py to reflect the base port and number of servers.
The base port is by default 2200.

A key needs to be provided:

```
python server.py -k=test_rsa.key
```

## Connecting to the server

The SSH client username needs to be in the format `username::hostname`.

For example, to connect as operator, and set the connection context to a device named "router5":

`ssh operator::router5@localhost -p 2200`

(The hostname portion informs the SSH server which directory to use for the `show` command files.)

## Using with ansible

### Set up the username for the connection

The network_mock server requires the username be in a particular format (see above).

This is used as the folder name from which the command output will be retrieved.

Example:

```
ansible_user: "{{ lookup('env', 'ansible_ssh_user') }}::{{ inventory_hostname }}"
```

### Set up the IP and port for the connection

The ansible invnetory should be updated such that each host uses a unique port on the SSH mock server and the `ansible_host` set to where the server was started.

```
vars:
  ansible_port: "{{ 2200 + play_hosts.index(inventory_hostname) }}"
  ansible_host: localhost
```

### Required files for ansible

Each platform requires certain `show` command output be available for Ansible modules to work.  Review the server output to see which `show` files commands are required.

Example:

```
INFO:NetworkServer:eos101: terminal length 0
INFO:NetworkServer:eos101: terminal width 512
INFO:NetworkServer:eos101: show version | json
INFO:NetworkServer:eos101: show hostname | json
```

Indicates that both `show version | json` and `show hostname | json` are required for the `eos_command` module.


## Examples

See the examples directory for a few examples

## Plugins

By default the following plugins are enabled:

`confmode`: Provide a `configure` context, only the prompt changes.
`showfs`: Return file output for commands
`help`: Provide the help
`history`: Provides the command history and `!5` support for previous commands

The enabled plugins can be changed from the command line.

```
python server.py -k ./test_rsa.key -e help
```
(enables only the help plugin)

### CommandRunner

The `cmdrunner` plugin retrieves command output from network devices and save the output to the local file system.

Both ` ansible` and `ansible_runner` will need to be installed:

```
pip install ansible
pip install ansible_runner
```

Enable the `cmdrunner` functionality from the command line when the server is started:

```
python server.py -k ./test_rsa.key -e confmode,showfs,help,history,cmdrunner
```

`cmdrunner` uses a series of `set` for configuration.

```
cmdrunner>help

CMDRUNNER

Run commands on devices and save the output to the local file system.

cmdrunner                               Enter the cmdrunner context
exit                                    Exit the cmdrunner context
set commands=show ver,show run          Specify the commands to run and save. (default=see help)
set hosts=nxos101,nxos102               Specify the target host to collect from. (default=current host)
set os=xxxx                             Set the OS for the target devices. (default=none)
set password=xxxx                       Set the password. (default=None)
set username=xxxx                       Set the username. (default=current user)
run                                     Collect the command output and save to local file system
```

Example:

Collect the default command output from several eos devices:

```
nxos101#cmdrunner
cmdrunner>set password=password
cmdrunner>set os=eos
cmdrunner>set hosts=eos101,eos102,eos103
cmdrunner>run
Running...
[✔] [eos103] ran 'show version | json'
[✔] [eos102] ran 'show version | json'
[✔] [eos101] ran 'show version | json'
[✔] [eos101] ran 'show hostname | json'
[✔] [eos103] ran 'show hostname | json'
[✔] [eos102] ran 'show hostname | json'
[✔] [eos101] ran 'show running-config'
[✔] [eos102] ran 'show running-config'
[✔] [eos103] ran 'show running-config'
[✔] [eos101] wrote './examples/configs/eos101/show version | json.txt'
[✔] [eos101] wrote './examples/configs/eos101/show hostname | json.txt'
[✔] [eos101] wrote './examples/configs/eos101/show running-config.txt'
[✔] [eos102] wrote './examples/configs/eos102/show version | json.txt'
[✔] [eos102] wrote './examples/configs/eos102/show hostname | json.txt'
[✔] [eos102] wrote './examples/configs/eos102/show running-config.txt'
[✔] [eos103] wrote './examples/configs/eos103/show version | json.txt'
[✔] [eos103] wrote './examples/configs/eos103/show hostname | json.txt'
[✔] [eos103] wrote './examples/configs/eos103/show running-config.txt'
```

Commands can be specified at the command line:

```
cmdrunner>set commands=show vrf,show vlan
cmdrunner>run
Running...
[✔] [eos101] ran 'show vrf'
[✔] [eos103] ran 'show vrf'
[✔] [eos102] ran 'show vrf'
[✔] [eos103] ran 'show vlan'
[✔] [eos102] ran 'show vlan'
[✔] [eos101] ran 'show vlan'
[✔] [eos101] wrote './examples/configs/eos101/show vrf.txt'
[✔] [eos101] wrote './examples/configs/eos101/show vlan.txt'
[✔] [eos102] wrote './examples/configs/eos102/show vrf.txt'
[✔] [eos102] wrote './examples/configs/eos102/show vlan.txt'
[✔] [eos103] wrote './examples/configs/eos103/show vrf.txt'
[✔] [eos103] wrote './examples/configs/eos103/show vlan.txt'
```

The default command set is the minimum command set output ansible requires but additionally include the running config.

```yaml
"ios":
- "show running-config"
"nxos":
- "show privilege"
- "show inventory"
- "show version"
- "show running-config"
"eos":
- "show version | json"
- "show hostname | json"
- "show running-config"
"vyos":
- "show config"
- "show configuration commands"
"all others":
- None
```

See the examples folder for an ansible playbook to see each of the devices in an inventory.


## Note

- Disabling ssh key checking during development can be done in the ansible.cfg
