# Unified Deploy App for Docker Stacks

This python tool used in jenkins or command line to deploy stacks to a docker cluster (modules are currently written for docker swarm deployment **ONLY!**)

# Requirements
  
    * python 3+
    * pip3

# Install Dependencies

From this directory run

    `install -r requirements.txt --user`

# Other Dependencies

AWS creds to the dev cloud must be setup and ssh key must be setup to initiate the SSL tunnel to a cluster

# How to run

From the current working directory (in this example its from the source code root) `deploy/main.py STACK_NAME CLUSTER_DOMAIN_NAME TIMEOUT`

    `CLUSTER_DOMAIN_NAME` = DNS record that points to docker cluster
    `STACK_NAME` = name of the stack to give/use for this deployment
    `TIMEOUT` = time out on check to see if all the tasks are running for a stack (in minutes)

# NOTE 

The Tool is expecting a valid docker compose file named `docker-compose-swarm.yml` and a valid .env with image keys containing the substring `image` in the key must present in the current working directory
