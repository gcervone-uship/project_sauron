#!/usr/bin/env python3
from plugins.consul_kv import get_consul, put_consul, is_consul_prefix, get_consul_by_prefix
from primitives.item_primitives import Item, make_valid, item_action, new_prefix

demo_items = [Item(key='demo_key', value='n'),
              Item(key='prefix_demo', value='x', prefix='prefix'),
              Item(key='prefix_demo2', value='y', prefix='prefix'),
              Item(key='prefix_demo3', value='z', prefix='prefix'),
              Item(key='invalid_prefix_demo', value='should fail', prefix='/failme')]

demo_list = [lambda s_item: make_valid(s_item),
             is_consul_prefix,
             put_consul]

copy_to_new_prefix = [lambda x: new_prefix(x, 'Outputs'),
                      put_consul]

for y in item_action(demo_items, demo_list):
    print(y)

print('\nNow we copy these items to a new prefix over writing them if they already exist\n')
source_items = get_consul_by_prefix(Item(prefix='prefix')).result

for x in item_action(source_items, copy_to_new_prefix):
    print('{}'.format(x))
