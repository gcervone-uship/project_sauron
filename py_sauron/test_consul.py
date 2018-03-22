from functools import reduce
from itertools import chain
from data_sources.consul_kv import get_consul, put_consul, is_consul_prefix
from data_sources.consul_kv import _get_consul, _put_consul
from consul import Consul

from primitives.item_primitives import Item, action_on_result, make_valid

test_list = [Item(key='test_key', value='n'),
             Item(key='prefix_test', value='x', prefix='test'),
             Item(key='invalid_prefix_test', value='should fail', prefix='/failme')]

#get_consul = lambda s_item: _get_consul(s_item, conn=Consul())
method_list = [lambda s_item: make_valid(s_item), is_consul_prefix, put_consul]

def wrapped_action(*args, **kwargs):
    print('Action {} {}'.format(args, kwargs))
    return action_on_result(*args, **kwargs)
          
per_item = lambda elem: reduce(lambda l, r: action_on_result(r, l), method_list, elem)
for y in map(per_item, test_list):
    print('- {}\n'.format(y))
                   
