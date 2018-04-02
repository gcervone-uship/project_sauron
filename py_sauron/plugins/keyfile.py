from itertools import chain, tee
import re

from utils import filter_both
from primitives.item_primitives import Result, join_prefix
    
def _keyfile_valid_key(s_item):
    valid_regex = r'^[0-9A-Z\_]+$'
    return re.match(valid_regex, s_item.key)

def _valid_prefix(s_item):
    if s_item.prefix is not None:
        return True
    return False

def serialize_keyfile(s_items, seperator='='):
    no_prefix, has_prefix = filter_both(lambda x: x.prefix is None, s_items)
    valid_keys, invalid_keys = filter_both(_keyfile_valid_key, no_prefix)
    valid, result = tee(valid_keys)
    invalid = chain(has_prefix, invalid_keys)
    to_lines = map(lambda x: '{}{}{}'.format(x.key,
                                             seperator,
                                             x.value), valid)
    output = '\n'.join(to_lines)
    return Result(result=result,
                  invalid=invalid,
                  output=output)

def serialize_shell(items):
    key_valid, key_invalid = filter_both(_keyfile_valid_key, items)
    no_prefix, has_prefix = filter_both(lambda x: x.prefix is None, key_valid)
    valid_prefix, invalid_prefix = filter_both(_valid_prefix, has_prefix)

    # If we had a valid prefix and a valid key, join them together to make a valid item
    joined_prefixes = map(join_prefix, valid_prefix)

    # Join all our valid results together and join our invalid results together
    valid, result = tee(chain(no_prefix, joined_prefixes))
    invalid = chain(key_invalid, has_prefix)

    # prepare an output with all of our valid items
    to_lines = map(lambda x: 'export {}={}'.format(x.key, x.value), valid)
    output = '\n'.join(to_lines)
    
    return Result(result=result,
                  invalid=invalid,
                  output=output)

def write_keyfiles(items,
                   destination,
                   separator='=',
                   overwrite=True):
    if overwrite:
        mode = 'w'
    else:
        mode = 'x'

    result = serialize_keyfile(items)
    with open(destination, mode) as f:
        f.write(result.output)
    return result
    
    
