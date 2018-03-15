import os.path
import time
import copy

import boto3
import yaml


def create_client():
    '''Purpose:  to create a AWS client for a cloudformation template and return client object'''
    client = boto3.client('cloudformation')
    return client


def create_load_stacks(services, swarm):
    '''Purpose: deploy ALB stacks for all services deployed to the swarm
    Dependencies - 
        Parameters - 
            services (dict) - dictionary of services deployed to the cluster with published port info 
                                and stack names
            swarm (dict)     - dictionary of the swarm that the services were deployed to
        Assumptions - 
            cloudformation template is located in the cloudformation directory
    '''
    cloudformation_client = create_client()
    docker_stack_name = next(iter(services))
    cf_stacks = []
    for service in services[docker_stack_name]:
        stack_cf_template_file = "./cloudformation/base.cfn.yml"
        template_body = create_template_body(stack_cf_template_file)
        if template_body:
            parameter_values = [
                swarm['swarmName'],
                services[docker_stack_name][service]["PublishedPort"],
                "academic",
                swarm['Environment'],
                docker_stack_name,
                'NONE',
                'NONE',
                'NONE'
            ]
            parameter_keys = get_parameters(template_body)
            parameters = create_parameters(
                parameter_keys, parameter_values)
            try:
                cloudformation_client.describe_stacks(
                    StackName=service.replace('_', '-'))
                stack_exists = True
            except:
                stack_exists = False
            if stack_exists:
                try:
                    response = cloudformation_client.update_stack(
                        StackName=service.replace('_', '-'),
                        TemplateBody=template_body,
                        Parameters=parameters
                    )
                except:
                    print("There was no updated required for - " + service.replace('_', '-'))
                    response = {}
                    response["ResponseMetadata"]["HTTPStatusCode"] = 200
            else:
                response = cloudformation_client.create_stack(
                    StackName=service.replace('_', '-'),
                    TemplateBody=template_body,
                    Parameters=parameters
                )
            if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
                print("Building " + service + " loadbalancer stack")
                cf_stacks.append(service.replace('_', '-'))

        else:
            print(stack_cf_template_file +
                  " does not exist, please check the repo to see if the template exists")
            sys.exit()

    print("----------------------------------------------------------------")
    stack_check_status = stacks_check(cloudformation_client, cf_stacks)
    print("Congrats! All CloudFormation Stacks are built!")
    stack_outputs(cloudformation_client, cf_stacks)


def create_template_body(template_file):
    '''Purpose: Create a String from a template file
    Dependencies - 
        Parameters - 
            template_file (str) - location of a template file
    Returns - 
            template (str) - the contents of the template file as a string
    '''
    if os.path.exists(template_file):
        with open(template_file, 'r') as template_body:
            template = template_body.read()
        return template
    else:
        return False


def get_parameters(template_body, use_defaults=True):
    '''Purpose: Get Parameters from a cf template file
    Dependencies - 
        Parameters - 
            template_body (str) - the contents of the template file as a string
    Returns - 
            parameters (list) - a list containing all the parameters of a file
    '''
    template_body_sanitize = template_body.replace('!', '')
    template_dict = yaml.load(template_body_sanitize)
    parameters = []
    for parameter in template_dict['Parameters']:
        if use_defaults:
            if "Default" not in template_dict['Parameters'][parameter]:
                parameters.append(parameter)
        else:
            parameters.append(parameter)
    return parameters


def create_parameters(keys, values):
    '''Purpose:  Create Parameters list for cf deploy
    Dependencies - 
        Parameters - 
            keys (list) - list of parameter keys
            values (list) - list of parameter values
    Returns - 
            parameters (list) - list of all parameter dictionaries
    '''
    parameters = []
    for key, value in zip(keys, values):
        parameter = {
            'ParameterKey': key,
            'ParameterValue': value
        }
        parameters.append(parameter)
    return parameters


def stacks_check(cloudformation_client, stacks):
    '''Purpose:  Loop through all the stacks and check the status of all the stacks
    Dependencies -
        Parameter   - 
            cloudformation_client (obj) - connection client to AWS
            stacks (list) - list of all the deployed cf stacks
    Returns -
        boolean - if all the stacks are complete return true, else return false
    '''
    stack_queue = copy.deepcopy(stacks)
    while True:
        for stack in stacks:
            if stack in stack_queue:
                print(stack + ": stack events - ")
                stack_status = check_stack_status(cloudformation_client, stack)
            if stack_status and (stack in stack_queue):
                print(stack + " COMPLETE!")
                stack_queue.remove(stack)
            print("\n")
        if not stack_queue:
            break
        print("----------------------------------------------------------------")
        time.sleep(10)

    if not stack_queue:
        return True
    else:
        return False


def check_stack_status(cloudformation_client, stack):
    '''Purpose:  Get status of a stack and print out the events
    Dependencies -
        Parameter   - 
            cloudformation_client (obj) - connection client to AWS
            stacks (list) - list of all the deployed cf stacks
    Returns -
        boolean - if all the stacks are complete return true, else return false
    '''
    stack_state = cloudformation_client.describe_stacks(StackName=stack)
    if "COMPLETE" in stack_state['Stacks'][0]['StackStatus']:
        return True
    else:
        response = cloudformation_client.describe_stack_events(StackName=stack)
        message_queue = []
        for event in response['StackEvents']:
            if event['LogicalResourceId'] not in message_queue:
                if event['LogicalResourceId'] != stack:
                    print(event['LogicalResourceId'] +
                          " status: " + event['ResourceStatus'])
                    message_queue.append(event['LogicalResourceId'])
        return False


def stack_outputs(cloudformation_client, cf_stacks):
    '''Purpose:  Print the outputs of the stack
    Dependencies -
        Parameter   - 
            cloudformation_client (obj) - connection client to AWS
            stacks (list) - list of all the deployed cf stacks
    '''
    for stack in cf_stacks:
        stack_output = cloudformation_client.describe_stacks(StackName=stack)
        print(stack + " - " + stack_output['Stacks']
              [0]['Outputs'][0]['OutputKey'] + ' - ' + stack_output['Stacks']
              [0]['Outputs'][0]['OutputValue'])
