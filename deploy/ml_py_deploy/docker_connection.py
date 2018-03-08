import subprocess
import os.path
import time
import base64

import boto3

from .shared import run_process


def cluster_conn(socket_file, cluster_DNS):
    '''Purpose:  create a named socket ssh tunnel to a swarm host

Dependencies -
    Parameter   - socket_file (str) - name of the domain socket to be saved on the local file system
    Parameter   - cluster_DNS (str) - domain name of cluster the app is trying to connect to

Returns -
    cluster_SSH_tunnel (obj) - subproccess object created by the ssh tunnel
'''
    print("Setting up connection to cluster", cluster_DNS, "at", socket_file)
    os.environ['DOCKER_HOST'] = "unix://" + socket_file
    cmd = 'ssh -nNT -o "ExitOnForwardFailure=yes" -o "StrictHostKeyChecking=no" -L %s:/var/run/docker.sock docker@%s' % (socket_file, cluster_DNS)
    cluster_SSH_tunnel = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                          shell=True)
    print("checking for sockfile...")
    count = 15
    while not os.path.exists(socket_file):
        time.sleep(1)
        count = count - 1
        print("...")
        if count == 0:
            print("ERROR: ssh connection to",
                  cluster_DNS, "failed.  Exiting...")
            cluster_SSH_tunnel.kill()
            return False
    else:
        print("ssh connection to",
              cluster_DNS, "complete.")
        return cluster_SSH_tunnel


def cluster_close(socket_file, tunnel):
    '''Purpose:  close ssh tunnel to a swarm host

Dependencies -
    Parameter   - socket_file (str) - name of the domain socket to be saved on the local file system
    Parameter   - cluster_DNS (str) - domain name of cluster the app is trying to connect to
'''
    print("Tearing down connection to cluster")
    if os.path.exists(socket_file):
        tunnel.kill()
        os.remove(socket_file)


def ecr_login():
    '''Purpose:  Get ECR creds from AWS and athenicate with ECR to get docker images

Dependencies -
    N/A

Returns -
    True or False (bool) - is the login to the ecr connected
'''
    print("Getting access token for the ecr...")
    ecr_client = boto3.client('ecr')
    response = ecr_client.get_authorization_token()
    ecr_auth_token = base64.b64decode(response['authorizationData'][
                                    0]['authorizationToken'])
    ecr_auth_token = ecr_auth_token.decode("utf-8")
    ecr_auth_endpoint = response['authorizationData'][0]['proxyEndpoint']
    ecr_username, ecr_password = ecr_auth_token.split(':')

    login_cmd = 'docker login --username %s --password %s %s' % (
        ecr_username, ecr_password, ecr_auth_endpoint)

    print("Logging into the docker repo {}".format(ecr_auth_endpoint))
    ecr_login = run_process(login_cmd)
    if ecr_login['error'] and ("ERROR" in ecr_login['error']):
        print("Docker repo login was not successful, please review prompt.")
        print(ecr_login['error'])
        return False
    else:
        print("Docker repo login successful")
        print(ecr_login['output'])
        return True
