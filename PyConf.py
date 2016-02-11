import paramiko
from time import time as time                   # used in: time_stamp()
from datetime import datetime as datetime       # used in: time_stamp()
import re
from threading import Thread
from queue import Queue
import yaml
from jinja2 import Template
import getpass

__author__ = 'Petr Ankudinov'


def time_stamp():
    """
    time_stamp function can be used for debugging or to display timestamp for specific event to a user
    :return: returns current system time as a string in Y-M-D H-M-S format
    """
    """
    :return:
    """
    time_not_formatted = time()
    time_formatted = datetime.fromtimestamp(time_not_formatted).strftime('%Y-%m-%d %H:%M:%S')
    return time_formatted


def search_prompt(a_string, mode='cisco'):
    """
    Check if string is a prompt or a command output.
    :param a_string: A string that can be a prompt.
    :param mode: What prompt we are looking for? Default is Cisco.
    :return: Return the prompt or None.
    """

    # Dictionary with regular expressions for different vendors.
    regexp_dict = {
        'cisco': [
            r'^.*#(\s)*$',          # Example: router#
            r'^.*>(\s)*$',          # Example: router>
            r'^.*\(.*\)#(\s)*$',    # Example: router(config)# or any submode
            r'^Destination filename \[startup-config\]\?',    # Example: Destination filename [startup-config]?
            r'^.*\[confirm\]',  # Example: This operation will remove all username related configurations with same name.
                                # Do you want to continue? [confirm]
        ]
    }

    re_match = None

    for regexp in regexp_dict[mode]:
        re_match = re.search(regexp, a_string)
        if re_match:
            return re_match.group(0)


def cli_session(command_list, remote_host_ip, username='cisco', password='cisco', debug_flag=0, timeout=2, mode='cisco'):
    """
    Initiates SSH session to a list of remote hosts and delivers list of commands to this host.
    :param command_list: list of commands to run on a host from the list
    :param remote_host_ip: a string with IP address of remote host to initiate SSH session
    :param username: login to access remote host
    :param password: password to access remote host
    :param debug_flag: if `true` additional info will be printed to debug CLI session
    :param timeout: SSH session timeout
    :return output of commands executed on host CLI, exit status, error code
    :mode CLI prompt regexp to be used
    """

    # Create an instance of SSHClient object
    ssh = paramiko.SSHClient()
    # Automatically add untrusted hosts (make sure okay for security policy in your environment)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Initiate SSH session
    ssh.connect(remote_host_ip, port=22, username=username, password=password, timeout=timeout)
    if debug_flag:
        print('SSH connection established to %s' % remote_host_ip)

    # use invoke_shell to establish and 'interactive session'
    ssh_session = ssh.invoke_shell()
    if debug_flag:
        print('Interactive SSH session established')

    buff_size = 4096
    stdout = ''
    stderr = ''

    def wait_for_prompt():
        stdout_temp = ''
        prompt = None
        start_time = time()
        while not prompt:
            while ssh_session.recv_ready():
                if debug_flag:
                    print('++ collecting data from the buffer')
                stdout_temp += ssh_session.recv(buff_size).decode()    # decode to convert Python3 bytes to string
                if ssh_session.recv_stderr_ready():
                    nonlocal stderr
                    stderr += ssh_session.recv_stderr(buff_size)

                for line in stdout_temp.splitlines():
                    find_prompt = search_prompt(line, mode=mode)
                    if find_prompt:
                        prompt = find_prompt
            running_time = time() - start_time
            if running_time > 60.0:
                print('++ Can not match CLI promt for 60 seconds on %s. Terminating.' % remote_host_ip)
                break
        return stdout_temp

    # wait for initial CLI prompt
    stdout += wait_for_prompt()

    # Execute CLI command
    for command in command_list:
        ssh_session.send(command)
        if debug_flag:
            print(r'+ sending command "%s" to the host %s' % (command.strip(), remote_host_ip))

        # collect data until prompt is matched
        stdout += wait_for_prompt()

        if debug_flag:
            print('+ data received, moving to the next command')

    # Terminate SSH session
    ssh.close()
    exit_status = ssh_session.recv_exit_status()    # nothing returned until session is closed

    return stdout, stderr, exit_status


def deliver_config(config, ip_addresses, username, password, mode='cisco'):

    log = ''

    # building IP and command list from text
    ip_list = [line.strip() for line in ip_addresses.splitlines() if line]
    command_list = [(line + '\n') for line in config.splitlines() if line]    # Note: blank lines will be removed

    # log displays collected CLI output for each host
    log.join('\n')
    log.join('#############################')
    log.join('########### LOG #############')
    log.join('#############################')
    log.join('\n')

    # delivering commands to all reachable devices
    successful = []         # SSH was successful
    unsuccessful = []       # SSH was not successful
    stdout = None

    for ip in ip_list:
        try:
            stdout, stderr, exit_status = cli_session(command_list, ip, username, password, debug_flag=0, mode=mode)
        except Exception as _:
            unsuccessful.append(ip)
        else:
            successful.append(ip)
        log.join('\n')
        log += ('#--#--# ' + str(ip) + '\n')
        log.join('\n')
        log += str(stdout)

    # printing list of hosts where SSH was successful
    log.join('\n')
    log.join('#############################')
    log.join('#### SUCCESSFUL #############')
    log.join('#############################')
    log.join('\n')

    for line in successful:
        log.join(line)

    # printing list of hosts where SSH was not successful
    log.join('\n')
    log.join('#############################')
    log.join('#### UNSUCCESSFUL ###########')
    log.join('#############################')
    log.join('\n')

    for line in unsuccessful:
        log.join(line)

    return log


class Task:

    def __init__(self, task_queue):
        self.filename = ''
        self.host_db = []
        self.task_queue = task_queue

    def read(self, filename=''):
        if filename:
            self.filename = filename
            try:
                yaml_file = open(self.filename, mode='r')
            except Exception as _:
                print('ERROR: Can not open task file.')
            else:
                yaml_data = yaml.load(yaml_file)
                yaml_file.close()
                for block in yaml_data:
                    if 'global_vars' in block:
                        global_vars = block['global_vars']
                    if 'host_db' in block:
                        self.host_db = block['host_db']
                    if 'hosts' in block:
                        # Merge local and global vars. Priority to local.
                        if global_vars:
                            block['vars'] = dict(global_vars, **block['vars'])
                        # extract hosts
                        host_list = []
                        for file in self.host_db:
                            host_db_file = open(file)
                            for host, tags in yaml.load(host_db_file).items():
                                if all(t in tags for t in block['hosts']):
                                    host_list.append(host)
                            host_db_file.close()
                        block['hosts'] = host_list
                        # convert template into config string
                        for step in block['tasks']:
                            conf_list = []
                            for file in step['template']:
                                j2 = open(file)
                                j2_temp = ''
                                for line in j2:
                                    j2_temp += line
                                t = Template(j2_temp)
                                conf = t.render(block['vars'])
                                conf_list.append(conf)
                            step['template'] = conf_list
                        # remove vars and add rendered task block to the list
                        block.pop('vars', None)

                        self.task_queue.put(block)

        else:
            print('ERROR: Task filename was not provided.')


class ExecuteTask(Thread):

    def __init__(self, host_queue, config_list, log_queue, usename, password, mode):
        Thread.__init__(self)
        self.host_queue = host_queue
        self.log_queue = log_queue
        self.config_list = config_list
        self.mode = mode
        self.username = usename
        self.password = password

    def run(self):

        while not self.host_queue.empty():
            log = ''
            host_ip = self.host_queue.get()
            for cfg_block in self.config_list:
                log += ('\n' + '++ Executing "' + cfg_block['name'] + '"\n')
                for cfg in cfg_block['template']:
                    log += deliver_config(cfg, host_ip, self.username, self.password, mode=self.mode)
                    self.log_queue.put(log)

            self.host_queue.task_done()


def main(filename):
    username = input('User: ')      # get username, will be echoed on the terminal
    password = getpass.getpass()    # get password, will not be echoed on the terminal, some IDE restrictions can apply

    print(time_stamp(), ': script started')

    task_queue = Queue()

    new_task = Task(task_queue)
    new_task.read(filename)

    while not task_queue.empty():
        host_queue = Queue()
        log_queue = Queue()
        task_block = task_queue.get()
        for host_ip in task_block['hosts']:
            host_queue.put(host_ip)
        config_list = task_block['tasks']

        while not host_queue.empty():

            for x in range(50):
                worker = ExecuteTask(host_queue, config_list, log_queue, username, password, mode=task_block['mode'])
                worker.daemon = True
                worker.start()

        host_queue.join()

        while not log_queue.empty():
            st = log_queue.get()
            print(st)

    print(time_stamp(), ': script stopped')
