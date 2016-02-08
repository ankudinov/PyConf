# PyConf
Multithreaded delivery of CLI commands to a set of hosts

PyConf is a script to deliver a number of CLI commands to a set of hosts.
Key features:
- No timeouts. Script is looking for a CLI promt after each command to reduce execution time.
 (To be honest, if promt can not be detected for 120 seconds. SSH is terminated by timeout.)
- It uses threading module to initiate multiple SSH connections to run even faster.
- It can execute complex tasks controlled by YAML file (like a very simple Ansible playbook).
- YAML file can specify a simple config to be delivered or a Jinja2 template and variables to render this template.
- Hosts can be selected from a simple YAML database by specifing tags. One line per host to be grep friendly.
