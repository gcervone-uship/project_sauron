from itertools import chain
import boto3
import yaml

from primitives.item_primitives import Item, Result

VALID_PREFIXES = ['Parameters', 'Outputs']


def _create_stack(stack_name, stack_template, build_parameters, cfn_client):
    EntityAlreadyExistsException = cfn_client.meta.client.exceptions.EntityAlreadyExistsException
    try:
        res = cfn_client.create_stack(StackName = stack_name,
                         TemplateBody = stack_template,
                         Parameters = build_parameters)
        stack_obj = cfn_client.Stack(res.stack_name)
    except EntityAlreadyExistsException as e:
        return None
    return stack_obj

def _update_stack(stack_name, stack_template, build_parameters, cfn_client):
    stack_object = cfn_client.Stack(stack_name)
    ClientError = stack_object.meta.client.exceptions.ClientError
    try:
        raw = stack_object.update(TemplateBody = stack_template,
                            Parameters = build_parameters)
    except ValidationError as e:
        pass
    # Reload the object even if we didn't change it
    # We may have passed in an arn instead of name
    # Reloading will make the .name and .stack_name correct for future references
    # To this stack object
    stack_object.reload()
    return stack_object
        
def create_cfn_stack(stack_name,
                 stack_template,
                 build_parameters={},
                 cfn_client = boto3.resource('cloudformation')):
    '''
    TODO: Wrap permissions exceptions so we can fall back if we've got default values
    '''
    v_stack_name = stack_name.replace('_', '-')
    res = _create_stack(v_stack_name, stack_template, build_parameters, cfn_client)
    if res:
        return res
    else:
        return _update_stack(v_stack_name, stack_template, build_parameters, cfn_client)
    

def _get_cfn_stack(stack_name, cfn_client):
    stack_object = cfn_client.Stack(stack_name)        
    ClientError = stack_object.meta.client.exceptions.ClientError
    try:
        stack_object.reload()
    except ClientError as e:
        return Result()
    _arams = stack_object.parameters
    _utputs = stack_object.outputs
    if _arams:
        params = map(lambda x: Item(key=x['ParameterKey'], value=x['ParameterValue'], prefix='Parameters'), _arams)
    else:
        params = []
    if _utputs:
        outputs = map(lambda x: Item(key=x['OutputKey'], value=x['OutputValue'], prefix='Outputs'), _utputs)
    else:
        outputs = []
    res = chain(outputs, params)
    return Result(result=res)
        
def _get_template(template_file):
    with open(template_file) as f:
        tem = f.read().replace('!','')
    return yaml.load(tem)

def _make_template_items(template_dict):
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

def get_cfn_template(template_file):
    t_dict = _get_template(template_file)
    r_items = _make_template_items(t_dict)
    return Result(result=r_items)


def get_cfn_stack(stack_name, cfn_resource=boto3.resource('cloudformation')):
    return _get_cfn_stack(stack_name, cfn_resource)
