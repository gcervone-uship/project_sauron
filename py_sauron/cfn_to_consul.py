#!/usr/bin/env python3

import yaml
import logging
from itertools import chain

import argparse

from primitives.item_primitives import Item, item_action, get_by_prefix, new_prefix
from primitives.item_primitives import operate, fill_values, drop_prefix
from plugins.cloudformation import get_cfn_stack, create_cfn_stack, get_cfn_template
from plugins.consul_kv import put_consul, get_consul_by_prefix, is_consul_prefix

#logging.basicConfig(level=logging.INFO)
logging.basicConfig(level=logging.DEBUG)

class RequireSourceName(argparse.Action):
    '''
    Action for argparse to require that --source-name has been provided
    '''
    def __call__(self, parser, namespace, values, option_string=None):
        if values == 'cfn_stack':
            if namespace.source_name:
                setattr(namespace, self.dest, values)
            else:
                parser.error('--source-name not set')
        setattr(namespace, self.dest, values)

def get_cli_opts():
    description = 'Load in parameters from a given source and write them out elsewhere'

    parser = argparse.ArgumentParser(description=description)
    # TODO: Add grouping to argparse to allow for exclusive options (Only let build template be set if using
    # the cfn_stack source
    parser.add_argument('-n', '--source-name',
                        dest='source_name',
                        help='Name to lookup from the source, Ex: stack name for cfn_stacks')

    parser.add_argument('-s', '--source',
                        default='consul',
                        help='Item source',
                        choices=['cfn_stack', 'consul', 'docker-cfn'])
#                        action=RequireSourceName)

    parser.add_argument('-p', '--source-prefix',
                        required=True,
                        dest='source_prefix',
                        help='Prefix to match source items on Ex: "Outputs" for cfn_stacks')

    parser.add_argument('-o', '--destination-prefix',
                        dest='destination_prefix',
                        required=True,
                        help='Prefix to append for the output, this defaults to the source prefix or stack name')

    parser.add_argument('-d', '--destination',
                        default='consul',
                        help='Item Destination',
                        choices=['consul'])

    parser.add_argument('--build-template',
                        dest='build_template',
                        type=argparse.FileType('r'),
                        help='If present, the stack will be built')

    parser.add_argument('--build-stack-name',
                        dest='build_stack_name',
                        help='The name to use if building a new stack')

    return parser.parse_args()


def handle_stack(s_stack_name, src_prefix):
    """
    Query cloudformation for our stack, grab all items matching the src_prefix
    (most likely Output) update the prefix to match the stack name, and return our
    final items
    """
    stack_res = get_cfn_stack(s_stack_name)
    if stack_res.result:
        stack_items = get_by_prefix(stack_res.result, src_prefix).result
        operations = [lambda x: new_prefix(x, s_stack_name)]
        final = item_action(stack_items, operations)
    else:
        raise KeyError('Stack {} not found'.format(s_stack_name))
    return final


def build_stack(build_name, raw_template, source_items=[]):
    """
    Pull the items from our cloudformation template, and get therequired parameters
    for our template. Fill in the required items from our source_items list, and build the
    template. Return the boto Stack object of the new stack
    """

    all_template_items = get_cfn_template(raw_template).result
    all_template_params = get_by_prefix(all_template_items, 'Parameters').result
    dropped_prefix = map(drop_prefix, all_template_params)
    filled = fill_values(dropped_prefix, source_items).result
    raw = create_cfn_stack(build_name, raw_template, filled)
    return raw

def get_services_from_docker(template_file):
    parsed = yaml.load(template_file)
    services = [x for x in parsed['services']]
    logging.debug('Services {}'.format(services))
    return services

def construct_stack_names(base_name, service):
    #stack_name =  ['{}-{}'.format(base_name, service) for service in services]
    stack_name = '{}-{}'.format(base_name, service)
    logging.debug('Stack Names: {}'.format(stack_name))
    return stack_name

def handle_multi_stacks(stack_names, src_prefix = 'Outputs'):
    result_items = []
    stack_names = list(stack_names)
    logging.debug('Handle Multi Stack Items: {}'.format(list(stack_names)))
    for stack in stack_names:
        stack_items = handle_stack(stack, src_prefix)
        logging.debug('Stack Items handle_multi: {}'.format(stack_items))
        updated_prefix = map(lambda x: x.clone(prefix=stack), stack_items)
        result_items.append(updated_prefix)
    logging.debug('Handle multi_stacks result_items: {}'.format(result_items))
    return chain.from_iterable(result_items)

def get_key(items, key):
    return filter(lambda x: x.key == key, items)

def prefix_to_key(items):
    return map(lambda x: x.clone(key=x.prefix, drop=['prefix']), items)

def do_docker_cfn(dockerfile, base_name):
    services = get_services_from_docker(dockerfile)
    stack_names = map(lambda x: construct_stack_names(base_name, x), services)
    all_stack_items = list(handle_multi_stacks(stack_names))
    only_urls = get_key(all_stack_items, 'StackUrl')
    return prefix_to_key(only_urls)


def main():
    args = get_cli_opts()

    # Check over some of our provided arguments, and make sure we have any dependent arguments
    if args.source == 'consul' and args.source_name:
        raise KeyError('source_name is invalid for consul source')
    if args.build_template and not args.build_stack_name and args.source != 'docker-cfn':
        raise ValueError('--build-stack-name is required for --build-template')
    if not args.build_template and args.build_stack_name:
        raise ValueError('--build-template is required for --build-stack-name')

    if args.source == 'cfn_stack':
        stack_name = args.source_name
        stack_prefix = args.source_prefix
        base_source_items = handle_stack(stack_name, stack_prefix)
    elif args.source == 'consul':
        base_source_items = get_consul_by_prefix(Item(prefix=args.source_prefix)).result
    elif args.source == 'docker-cfn':
        base_source_items = do_docker_cfn(args.build_template, args.source_name)

    if args.build_template and not args.source == 'docker-cfn':
        """
        take our source items, fill them into the parameters of the template
        build the template, and return the items from the Outputs section of
        the template
        """

        if base_source_items is None:
            available_source_items = []
        else:
            available_source_items = base_source_items

        fill_with = map(drop_prefix, available_source_items)
        raw_template = args.build_template.read()
        raw = build_stack(args.build_stack_name, raw_template, fill_with)
        stack_items = handle_stack(args.build_stack_name, 'Outputs')
        source_items = list(stack_items)
    else:
        """
        if we're not building a stack, pass the items directly from the source
        to the destination
        """
        source_items = list(base_source_items)

    logging.debug('Source Items: {}'.format(source_items))
    # Update the items with the new prefix if required
    if args.destination_prefix:
        dest_prefix = [lambda x: new_prefix(x, args.destination_prefix)]
    else:
        dest_prefix = [lambda x: x]
    
    if args.destination == 'consul':
        dest_actions = [is_consul_prefix,
                        put_consul]

    # join the actions to be performed on the prefix, and the actions for the destination
    actions = dest_prefix + dest_actions

    # Perform our accumulated actions our our source_items
    for operation in operate(item_action(source_items, actions)):
        logging.debug(operation)

if __name__ == '__main__':
    main()
