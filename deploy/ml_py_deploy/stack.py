import os.path
import time
import re
import copy

import yaml

from .shared import run_process, write_stack_yaml


def deploy_stack(stack_name, timeout):
    '''Purpose:  Deploy a docker swarm stack from an docker-compose file and an env file

Dependencies -
    Parameter   - stack_name (str) - name of the stack deing deployed
                  timeout (int) - timeout in seconds to make sure a stack is up and running
'''
    print("Deploying", stack_name)
    deploy_cmd = "docker stack deploy --compose-file docker-compose-swarm.yml --with-registry-auth %s" % (
        stack_name)
    env_keys = get_env_keys()
    if env_keys:
        envs = set_envs(env_keys)
        if envs:
            output = run_process(deploy_cmd)
            print(output['output'])
            if output['error']:
                print(output['error'])
            stack_services = get_stack_services(stack_name)
            stack_check_status = stack_check(stack_services, timeout)
            if stack_check_status:
                print("{} successfully deployed! WOOT!".format(stack_name))
                stack_file = write_stack_yaml(stack_name, stack_services)
                print(
                    "{} has been created and ready for the next stage".format(stack_file))
            else:
                print("{} did not deploy correctly! Bummer Dude!".format(stack_name))


def get_env_keys():
    '''Purpose:  Get Environment Keys needed from a docker compose file (images and ports)

Dependencies -
    Assumption  - docker-compose-swarm.yml (file) - docker compose file used to define a stack.
                  It is assumed that the file is in the root of where the app is being executed from

Returns -
    envs (list) - a list of keys found in the docker-compose file
'''
    compose_file = "./docker-compose-swarm.yml"
    if os.path.exists(compose_file):
        envs = []
        env_lines = []
        with open(compose_file, 'rt') as in_file:
            for line in in_file:
                if "${" in line:
                    env_lines.append(line)

        for env_line in env_lines:
            env_line.strip()
            env_list = env_line.split()
            env = re.sub('[$\{\}"]', '', env_list[1])
            envs.append(env)

        return envs

    else:
        print("ERROR:", compose_file, "missing!")
        return False


def set_envs(keys):
    '''Purpose:  Get list of keys and read values from an .env file, sets these environment variables
          for the deployment as envrionment variables and returns a dictionary of the
          key value pair

Dependencies -
    Parameter   - keys (list) - name of the stack deing deployed
    Assumption  - .env (file) - environment variable file used to define all the vars for
                  a stack at runtime.  It is assumed that the file is in the root of where the app is being
                  executed from

Returns -
    envs (dictionary) - a dictionary of environment variables to be set
'''
    envFile = "./.env"
    if os.path.exists(envFile):
        envs = {}
        with open(envFile, 'rt') as in_file:
            for line in in_file:
                for key in keys:
                    envList = line.split('=')
                    os.environ[envList[0]] = envList[1].rstrip('\n')
                    envs[envList[0]] = envList[1]

        return envs

    else:
        print("ERROR:", envFile, "missing!")
        return False


def stack_check(stack, timeout):
    '''Purpose:  Loop through all the services in a stack and see if all the tasks are running for each service

Dependencies -
    Parameter   - stack (dict) - dictionary of all the services in a stack with basic info for each stack
    Parameter   - timeout (int) - number of seconds if the loop is not successful

Returns -
    boolean - if all the service tasks are running within the time limit return true, else return false'''
    serviceQueue = {}
    for service in stack.keys():
        if 'PublishedPort' in stack[service]:
            serviceQueue[service] = stack[service]
    timer = 0
    while True:
        for service in stack.keys():
            ServiceStatus = check_service_status(
                service, stack[service])
            if ServiceStatus and service in serviceQueue:
                del serviceQueue[service]
        if not serviceQueue or timer == timeout:
            break
        time.sleep(10)
        timer = timer + 10
    if not serviceQueue:
        return True
    else:
        return False


def check_service_status(service_name, service_info):
    '''Purpose:  Check to see the number of running tasks for a service for in a stack and return a boolean
          if the number of running tasks == replica count defined by the serivce

Dependencies -
    Parameter   - service_name (str) - name of a service in a stack
    Parameter   - service_info (dict) - basic info for a given service defined by docker service inspect

Returns -
    boolean - if running tasks != replica count return true else return false
'''
    get_current_running_tasks_command = "docker service ps --filter 'desired-state=running' --format '{{.Image}} {{.CurrentState}}' %s | grep \"%s\" | grep -v \"second\" | wc -l" % (service_name, service_info[
        'image'])
    current_running_tasks = run_process(get_current_running_tasks_command)
    print("{} has {} of {} running tasks for over a minute".format(
        service_name, current_running_tasks['output'], service_info['replicas']))
    if int(current_running_tasks['output']) != int(service_info['replicas']):
        return False
    else:
        return True


def get_stack_services(stack_name):
    '''Purpose:  From the name of the stack get all the services attached to the stack and create
          a dictionary of services with the latest image deployed and the replica count for
          each service

Dependencies -
    Parameter   - stack_name (str) - name of the stack deing deployed

Returns -
    services (dict) - a dictionary of services and basic information on the service
                            image (str) - the image deployed
                            replicas (str) - the number of replicas associated to the service
                            PublishedPort (str) - the port the swarm is listening to (this maybe
                               null if this is an internal service)
'''
    services = {}
    get_services_command = "docker stack services --format '{{.Name}}' %s" % (
        stack_name)
    output = run_process(get_services_command)
    if len(output['error']) > 0:
        print(output['error'])
        return False
    else:
        for service in output['output'].splitlines():
            if len(service) != 0:
                service_info = get_service_info(service)
                if service_info:
                    services[service] = service_info
                else:
                    print("ERROR: Could not get service info for", service)
        return services


def get_service_info(service):
    '''Purpose:  Get Basic Info about a docker service

Dependencies -
    Parameter   - service (str) - name of the service in a stack

Returns -
    service_info (dict) - a dictionary of elements of a service
                            image (str) - the image deployed
                            replicas (str) - the number of replicas associated to the service
                            PublishedPort (str) - the port the swarm is listening to (this maybe
                               null if this is an internal service)
'''
    get_service_info_command = 'docker service inspect %s --format=\'{{ ((index .Spec.Labels "com.docker.stack.image") 0)}}#{{.Spec.Mode.Replicated.Replicas}}#{{ ( index .Endpoint.Ports 0 )  }}\'' % (
        service)
    service_info_output = run_process(get_service_info_command)
    service_info_list = service_info_output['output'].split('#')
    if len(service_info_list) == 3:
        image, replicas, network_info = service_info_list
        # Could not Pubslished  Port from format since .Endpoint.Ports is a list
        published_port = network_info.split(' ').pop(3)
        service_info = {"image": image, "replicas": replicas,
                    "PublishedPort": published_port}
    else:
        get_service_info_command = 'docker service inspect %s --format=\'{{ ((index .Spec.Labels "com.docker.stack.image") 0)}}#{{.Spec.Mode.Replicated.Replicas}}\'' % (
        service)
        service_info_output = run_process(get_service_info_command)
        service_info_list = service_info_output['output'].split('#')
        image, replicas = service_info_list
        service_info = {"image": image, "replicas": replicas}

    return service_info


def get_stacks(stack_file):
    '''Purpose:  import contents of stack file into a dictionary

Dependencies -
    Parameter   -
                    stack_file (str) - file location of stack file from deploy

Returns -
    stacks (dict) - a dictionary of stacks and Published Ports
'''
    stack_name = stack_file.replace('./', '').replace('.yaml', '')
    services = {}
    services[stack_name] = {}
    with open(stack_file, 'r') as stream:
        stacks = yaml.load(stream)
    for stack, info in stacks.items():
        if 'PublishedPort' in info:
            service = {"name": stack, "PublishedPort": info['PublishedPort']}
            services[stack_name][stack] = service
    return services


def get_swarm(cluster_DNS):
    '''Purpose:  From cluster DNS record get tag for target group via a dictionary as a map

        Dependencies -
            Parameter - cluster_DNS (str) - cluster DNS record

        Returns -
            cluster_map[cluster_DNS] (dict) - AWS tag for swarm cluster
    '''
    cluster_map = {
        'swarm-dev.mldev.cloud': {'swarmName': 'Dev-Alpha', 'Environment': 'dev'},
        'swarm-int.mldev.cloud': {'swarmName': 'Integration-Alpha', 'Environment': 'qa'},
        'swarm-prod.mldev.cloud': {'swarmName': 'Prod-Delta', 'Environment': 'prod'}
    }
    return cluster_map[cluster_DNS]
