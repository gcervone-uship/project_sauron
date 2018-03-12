#!/usr/bin/env python3
import sys
import os.path
import random

from ml_py_deploy.docker_connection import cluster_conn, cluster_close, ecr_login
from ml_py_deploy.stack import deploy_stack


if len(sys.argv) != 4:
    message = """Usage: deploy/main.py STACK_NAME CLUSTER_DOMAIN_NAME TIMEOUT

            STACK_NAME = name of the stack to give/use for this deployment
            CLUSTER_DOMAIN_NAME = DNS record that points to docker cluster            
            TIMEOUT = time out on check to see if all the tasks are running for a stack (in minutes)

        ** NOTE that the deploy is expecting a valid docker compose file named \"docker-compose-swarm.yml\" and
        a valid .env with image keys containing the substring \"image\" in the key must present in the current working directory
"""

    print(message)
    sys.exit()

# get position arguments for script
stack_name, cluster_DNS, timeout_minutes = sys.argv[1:] 

if (os.path.exists('./docker-compose-swarm.yml')==False) and (os.path.exists('./.env')==False):
    print("ERROR!  I am missing a compose file and/or an .env file. Please provide those files in the root directory of where I am being run from")
    sys.exit()

timeout_seconds = timeout_minutes * 60

if ecr_login():
    socket_file = "/tmp/" + \
        stack_name + str(random.randrange(1000)) + ".sock"
    cluster = cluster_conn(socket_file, cluster_DNS)
    if cluster:
        deploy_stack(stack_name, timeout_seconds)
        cluster_close(socket_file, cluster)
    else:
        sys.exit()
else:
    sys.exit()
