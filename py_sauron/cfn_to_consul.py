import argparse
import yaml

from primitives.item_primitives import Item, item_action, get_by_prefix, new_prefix, operate, fill_values, drop_prefix
from plugins.cloudformation import get_cfn_stack, create_cfn_stack, _make_template_items, get_cfn_template
from plugins.consul_kv import put_consul, get_consul_by_prefix, is_consul_prefix

class RequireSourceName(argparse.Action):
    '''
    Action for argparse to require that --source-name has been provided
    '''
    def __call__(self, parser, namespace, values, option_string=None):
        if values == 'cfn_stack':
            if self.source_name:
                setattr(namespace, self.dest, values)
            else:
                parser.error('--source-name not set')
        setattr(namespace, self.dest, values)
        
def get_cli_opts():
    description = 'Load in parameters from a given source and write them out elsewhere'
    
    parser = argparse.ArgumentParser(description=description)
    # TODO: Add grouping to argparse to allow for exclusive options (Only let build template be set if using
    # the cfn_stack source

    parser.add_argument('-s', '--source',
                        default='consul',
                        help='Item source',
                        choices=['cfn_stack', 'consul'],
                        action=RequireSourceName,
    )
    parser.add_argument('-n', '--source-name',
                        dest='source_name',
                        help='Name to lookup from the source, Ex: stack name for cfn_stacks')
                        
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
                        dest = 'build_template',
                        type=argparse.FileType('r'),
                        help='If present, the stack will be built')
    parser.add_argument('--build-stack-name',
                        dest = 'build_stack_name',
                        help='The name to use if building a new stack')
                           

    return parser.parse_args()



def handle_stack(stack_name, src_prefix):
    """
    Query cloudformation for our stack, grab all items matching the src_prefix
    (most likely Output) update the prefix to match the stack name, and return our
    final items
    """
    stack_res = get_cfn_stack(stack_name)
    if stack_res.result:
        stack_items = get_by_prefix(src_prefix, stack_res.result).result
        operations = [lambda x: new_prefix(x, stack_name)]
        final = item_action(stack_items, operations)
    else:
        raise KeyError('Stack {} not found'.format(stack_name))
    return final


def build_stack(build_name, raw_template, source_items=[]):
    """
    Pull the items from our cloudformation template, and get therequired parameters
    for our template. Fill in the required items from our source_items list, and build the
    template. Return the boto Stack object of the new stack
    """
    
    all_template_items = get_cfn_template(raw_template).result
    all_template_params = get_by_prefix('Parameters', all_template_items).result
    dropped_prefix = map(drop_prefix, all_template_params)
    filled = fill_values(dropped_prefix, source_items).result
    raw = create_cfn_stack(build_name, raw_template, filled)
    return raw
    

if __name__ == '__main__':
    args = get_cli_opts()

    # Check over some of our provided arguments, and make sure we have any dependent arguments
    if args.source == 'consul' and args.source_name:
        raise KeyError('source_name is invalid for consul source')
    if args.build_template and not args.build_stack_name:
        raise ValueError('--build-stack-name is required for --build-template')
    if not args.build_template and args.build_stack_name:
        raise ValueError('--build-template is required for --build-stack-name')

    if args.source == 'cfn_stack':
        stack_name = args.source_name
        stack_prefix = args.source_prefix
        base_source_items = handle_stack(stack_name, stack_prefix)
    elif args.source == 'consul':
        base_source_items = get_consul_by_prefix(Item(prefix=args.source_prefix)).result

        
    if args.build_template:
        """
        take our source items, fill them into the parameters of the template
        build the template, and return the items from the Outputs section of
        the template
        """
        fill_with = map(drop_prefix, base_source_items)
        raw_template = args.build_template.read()
        raw = build_stack(args.build_stack_name, raw_template, fill_with)
        stack_items = handle_stack(args.build_stack_name, 'Outputs')
        source_items = list(stack_items)
    else:
        """
        if we're not building a stack, pass the items directly from the source
        to the destination
        """
        source_items = base_source_items


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
    for x in operate(item_action(source_items, actions)):
        print(x)
