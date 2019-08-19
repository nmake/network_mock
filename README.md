# Network Mock

`network_mock` is a simple ssh server that can respond to network device `show` commands. It was authored as a debugging tool used during local development.

## Usage

```
usage: server.py [-h] [-b BASE_PORT] [-d DIRECTORY] [-p PASSWORD]
                 [-u USERNAME] [-c SERVER_COUNT] -k SSH_KEY

optional arguments:
  -h, --help            show this help message and exit
  -b BASE_PORT,       --base-port BASE_PORT
                        Base port for the SSH server. (default: 2200)
  -d DIRECTORY,       --directory DIRECTORY
                        The path to the device/commands directories. (default:
                        ./examples/configs)
  -p PASSWORD,        --password PASSWORD
                        The SSH server authentication password. (default:
                        None)
  -u USERNAME,        --username USERNAME
                        The SSH server authentication username. (default:
                        None)
  -c SERVER_COUNT,    --server-count SERVER_COUNT
                        The number of SSH servers to start. (default: 10)
  -k SSH_KEY,         --ssh_key SSH_KEY
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

## Note

- Disabling ssh key checking during development can be done in the ansible.cfg
