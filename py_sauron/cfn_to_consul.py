from primitives.item_primitives import item_action, get_by_prefix, new_prefix, operate, fill_values
from plugins.cloudformation import get_cfn_stack, create_cfn_stack, _make_template_items
from data_sources.consul_kv import put_consul, get_consul, is_consul_prefix

import argparse
import yaml

def get_cli_opts():
    description = 'Load in parameters from a given source and write them out elsewhere'
    parser = argparse.ArgumentParser(description=description)
    # TODO: Add grouping to argparse to allow for exclusive options (Only let build template be set if using
    # the cfn_stack source
    parser.add_argument('--build-template',
                        dest = 'build_template',
                        required=False,
                        type=argparse.FileType('r'),
                        help='If present, the stack will be built')
    parser.add_argument('-s', '--source',
                        default='cfn_stack',
                        help='Item source',
                        choices=['cfn_stack', 'consul'],
    )
    parser.add_argument('-n', '--source-name',
                        required=True,
                        dest='source_name',
                        help='Name to lookup from the source, Ex: stack name for cfn_stacks')
                        
    parser.add_argument('-d', '--destination',
                        default='consul',
                        help='Item Destination',
                        choices=['consul'])

    parser.add_argument('-p', '--source-prefix',
                        dest='source_prefix',
                        default='Outputs',
                        help='Prefix to match source items on Ex: "Outputs" for cloudformation related operations')

    parser.add_argument('-o', '--destination-prefix',
                        dest='destination_prefix',
                        default=None,
                        help='Prefix to append for the output, this defaults to the source prefix or stack name')

    return parser.parse_args()



def handle_stack(stack_name, stack_prefix):
    stack_res = get_cfn_stack(stack_name)
    if stack_res.result:
        _tack_items = list(stack_res.result)
        stack_items = get_by_prefix(stack_prefix, _tack_items).result
        operations = [lambda x: new_prefix(x, stack_name)]
        final = item_action(stack_items, operations)
    else:
        raise KeyError('Stack {} not found'.format(stack_name))
    return final

def build_stack(source_name, template_file_object):
    create_cfn_stack(source_name, template_file_object.read())

if __name__ == '__main__':
    args = get_cli_opts()
    if args.build_template:
        create_cfn_stack(args.source_name, args.build_template.read())        
        
    if args.source == 'cfn_stack':
        stack_name = args.source_name
        stack_prefix = args.source_prefix
        source_items = handle_stack(stack_name, stack_prefix)
    elif args.source == 'consul':
        source_items = get_consul_by_prefix(Item(prefix=args.source_prefix)).result
        
    if args.destination_prefix:
        dest_prefix = [lambda x: new_prefix(x, args.destination_prefix)]
    else:
        dest_prefix = [lambda x: x]

    if args.destination == 'consul':
        dest_actions = [is_consul_prefix,
                        put_consul]

    actions = dest_prefix + dest_actions

    print(operate(item_action(source_items, actions)))
