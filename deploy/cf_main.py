#!/usr/bin/env python3
import sys
import os.path
import random

from ml_py_deploy.cloudformation import create_load_stacks
from ml_py_deploy.stack import get_stacks, get_swarm

if len(sys.argv) != 4:
    message = """Usage: deploy/cf_main.py TYPE STACK_NAME CLUSTER_DNS

            TYPE = data / load. Data for data resources that need to be deployed or load for load balancers that 
                   to talk to a cluster for a service
            STACK_NAME = name of the stack to give/use for this deployment
            CLUSTER_DOMAIN_NAME = DNS record that points to docker cluster

        ** NOTE that the cloudformation deploy is expecting a valid cloudformation template  
"""

    print(message)
    sys.exit()

deploy_type = sys.argv[1]


if deploy_type == 'load':
    stack_name, cluster_DNS = sys.argv[2:] 
    stack_file = "./%s.yaml" % (stack_name)
    if (os.path.exists(stack_file) == False):
        print(stack_file + " does not exists.  Have you deployed your stack to the cluster yet?  Please run deploy/main.py first for your stack")
        sys.exit()
    else:
        swarm = get_swarm(cluster_DNS)
        services = get_stacks(stack_file)
        create_load_stacks(services, swarm)

else:
    print("This section is for the data cloudformation which will be in iteration 2")
    # coming in second iteration
