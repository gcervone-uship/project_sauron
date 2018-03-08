import subprocess

import yaml


def run_process(cmd):
    '''Purpose:  Start a child process and return the stdout and stderr

Dependencies -
    Parameter   - cmd (str) - the shell command you would like to run

Returns -
    message (dict) - a dictionary with two elements
                    output (str) - the stdout of the process
                    error (str)  - the stderr of the process
'''

    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = process.communicate()
    output = stdout.strip().decode()
    error = stderr.strip().decode()
    message = {'output': output, 'error': error}
    return message


def write_stack_yaml(stack_name, stack):
    '''Purpose:  create yaml file for loadbalancer creation

Dependencies -
    Parameter   - stack_name (str) - name of the deployed stack
    Parameter   - stack (dict) - dictionary of service info

Returns -
    stack_file (str) - yaml file with list of services in a stack and basic service info
'''
    stack_file = "{}.yaml".format(stack_name)
    with open(stack_file, 'w') as output:
        yaml.dump(stack, output, default_flow_style=False)
    return stack_file
