#!/usr/bin/env python3
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

template_params = get_by_prefix(cfn_results, 'Parameters').result
cfn_required = map(drop_prefix, template_params)

deduplicated_source_items = dedup_prefix_keys(keyfile_results).result
keyfile_items = map(drop_prefix, deduplicated_source_items)

# fill in the required paramaters for the cloudformation template
# fill_values will raise an exception by default if there are missing params
filled = fill_values(cfn_required, keyfile_items)

for x in filled.result:
    print(x)

