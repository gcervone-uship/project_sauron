from primitives import item_primitives
from primitives.item_primitives import Result, Item
from primitives.item_primitives import get_by_prefix, drop_prefix, dedup_prefix_keys, fill_values


d_template_items = [Item(prefix='Parameters', key='Has'),
                    Item(key='Hass', value='maybse'),
                    Item(prefix='Parameters',key='Hasss'),
                    Item(prefix='Parameters', key='Has_another_key')]

d_keyfile_items = [Item(key='Hass', value='maybe'),
                   Item(key='Has', value='maybse'),
                   Item(key='Has_another_key', value='another_default')]


# Mock up the how we would actually be recieving the results
cfn_results = Result(result=iter(d_template_items)).result
keyfile_results = Result(result=iter(d_keyfile_items)).result

__n_required = get_by_prefix('Parameters', cfn_results).result
_fn_required = dedup_prefix_keys(__n_required)
cfn_required = map(drop_prefix, _fn_required.result)

_eyfile_items = dedup_prefix_keys(keyfile_results)
keyfile_items = map(drop_prefix, _eyfile_items.result)


filled = fill_values(cfn_required, keyfile_items)

for x in filled.result:
    print(x)
