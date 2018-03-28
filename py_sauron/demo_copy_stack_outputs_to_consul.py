from primitives.item_primitives import get_by_prefix, drop_prefix, dedup_prefix_keys, fill_values, item_action, new_prefix, operate
from plugins.cloudformation import get_cfn_stack
from data_sources.consul_kv import put_consul, get_consul, is_consul_prefix


stack_name = 'testing-exceptions'

operations = [lambda x: new_prefix(x, stack_name),
              put_consul]

stack_res = get_cfn_stack(stack_name)

if stack_res.result:
    _tack_items = list(stack_res.result)
    stack_items = get_by_prefix('Outputs', _tack_items).result
else:
    raise KeyError('Stack {} not found'.format(stack_name))


final = operate(item_action(stack_items, operations))

print(final)
