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

To run the script, write your own host-db.yml, task-file.yml and templates and execute it in following way:
```text
cd /path-to-script-directory/
./pconf.py ./task/configure-a-vlan.yml
```
Script will ask for your username and password and start delivery.  
Proposed directory structure:

| dir/file  | comments                                               |
| --------- | -------------------------------------------------------|
| Templates | a folder with Jinja2 templates or configs              |
| db        | host databases, YAML                                   |
| task      | task files (aka playbooks), YAML                       |
| PyConf.py | a piece of unreadable code                             |
| pconf.py  | starts the script with YAML task as mandatory argument |

NOTE: This is a very first version. A lot to be improved. **Any suggestions are welcome.**

TODO:
- Error checks of all kinds.
- Clean and readable code. Lowest priority, obviously. =)
- Logical OR between tags.
- Option to print config generated from template instead of delivery.
- Web interface (Flask) and/or interactive mode.
- Progress bar or similar while script is running.
- Move regexp dictionary to a faile.
