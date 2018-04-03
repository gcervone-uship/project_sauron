#!/usr/bin/env python3
from primitives.item_primitives import item_action, get_by_prefix, new_prefix, operate
from plugins.cloudformation import get_cfn_stack
from plugins.consul_kv import put_consul, get_consul, is_consul_prefix


stack_name = 'testing-exceptions'

operations = [lambda x: new_prefix(x, stack_name),
              put_consul]

stack_res = get_cfn_stack(stack_name).result

if stack_res:
    stack_items = get_by_prefix(stack_res, 'Outputs').result
else:
    raise KeyError('Stack {} not found'.format(stack_name))


final = operate(item_action(stack_items, operations))

print(final)
