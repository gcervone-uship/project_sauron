from itertools import chain
import yaml

import boto3

from primitives.item_primitives import Item, Result


VALID_PREFIXES = ['Parameters', 'Outputs']


def _create_stack(stack_name, stack_template, build_parameters, cfn_client):
    AlreadyExistsException = cfn_client.meta.client.exceptions.AlreadyExistsException
    try:
        res = cfn_client.create_stack(StackName = stack_name,
                         TemplateBody = stack_template,
                         Parameters = build_parameters)
        # Get a cloudformation waiter, and wait for the stack to finish building
        waiter = cfn_client.meta.client.get_waiter('stack_create_complete')
        waiter.wait(StackName=stack_name)
        stack_obj = cfn_client.Stack(res.stack_name)
    except AlreadyExistsException as e:
        return None
    return stack_obj

def _update_stack(stack_name, stack_template, build_parameters, cfn_client):
    stack_object = cfn_client.Stack(stack_name)
    ClientError = stack_object.meta.client.exceptions.ClientError
    try:
        raw = stack_object.update(TemplateBody = stack_template,
                            Parameters = build_parameters)
        # Get a cloudformation waiter and wait for the stack to finish updating
        waiter = cfn_client.meta.client.get_waiter('stack_update_complete')
        waiter.wait(StackName=stack_name)
    # We will get a ClientError ValidationError if the template does not need to be updated    
    except ClientError as e:
        pass
    """ Reload the object even if we didn't change it
    We may have passed in an arn instead of name
    Reloading will make the .name and .stack_name correct for future references
    To this stack object
    """
    stack_object.reload()
    return stack_object
        
def create_cfn_stack(stack_name,
                 stack_template,
                 build_parameters=[],
                 cfn_client = boto3.resource('cloudformation')):
    """
    TODO: Wrap permissions exceptions so we can fall back if we've got default values
    """
    build_params = [{'ParameterKey': x.key, 'ParameterValue': x.value} for x in build_parameters]
    v_stack_name = stack_name.replace('_', '-')
    res = _create_stack(v_stack_name, stack_template, build_params, cfn_client)
    if res:
        return res
    else:
        return _update_stack(v_stack_name, stack_template, build_params, cfn_client)
    

def _get_cfn_stack(stack_name, cfn_client):
    """
    Query cloudformation to get the Parameters and Outputs for a given stack
    """
    stack_object = cfn_client.Stack(stack_name)        
    ClientError = stack_object.meta.client.exceptions.ClientError
    # Reload the stack_object to ensure we've recieved a valid name/arn
    try:
        stack_object.reload()
    except ClientError as e:
        return Result()
    stack_params = stack_object.parameters
    stack_outputs = stack_object.outputs
    if stack_params:
        params = map(lambda x: Item(key=x['ParameterKey'], value=x['ParameterValue'], prefix='Parameters'), stack_params)
    else:
        params = []
    if stack_outputs:
        outputs = map(lambda x: Item(key=x['OutputKey'], value=x['OutputValue'], prefix='Outputs'), stack_outputs)
    else:
        outputs = []
    res = chain(outputs, params)
    return Result(result=res)
        
def _get_template(template_yaml):
    """
    Take a raw cloudformation template, remove exclamation marks so we can easily parse it
    and return a dictionary of the template
    """
    tem = template_yaml.replace('!','')
    return yaml.load(tem)


def _make_template_items(template_dict):
    """
    Take a template dictionary, and wrap the Parameters and Outputs into a list Item classes
    """
    item_acc = []
    for prefix, keys in template_dict.items():
        if prefix in VALID_PREFIXES:
            for inner_key, inner_value in keys.items():
                if 'Default' in inner_value:
                    value = inner_value['Default']
                else:
                    value = None
                item_acc.append(Item(prefix=prefix,
                                     key=inner_key,
                                     value=value))
        
    return item_acc

def get_cfn_template(template_yaml):
    """
    Take a raw cfn template and return a result object of the template's items
    """
    t_dict = _get_template(template_yaml)
    r_items = _make_template_items(t_dict)
    return Result(result=r_items)


def get_cfn_stack(stack_name, cfn_resource=boto3.resource('cloudformation')):
    """
    Get the Items associated with a given stack (by name or arn)
    """
    return _get_cfn_stack(stack_name, cfn_resource)
