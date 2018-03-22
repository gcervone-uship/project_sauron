from itertools import chain
import re
from utils import filter_both
from data_sources.items import join_prefix
    
def _keyfile_valid_key(item):
    valid_regex = r'^[0-9A-Z\_]+$'
    return re.match(valid_regex, item['key'])

def _valid_prefix(item):
    if item['prefix']:
        return True
    return False

def serialize_keyfile(items, seperator='='):
    v_prefixes = filter_both(lambda x: x['prefix'] == None, items)
    v_keys = filter_both(_keyfile_valid_key, v_prefixes['match'])
    valid = v_keys['match']
    invalid = chain(v_prefixes['no_match'], v_keys['no_match'])
    to_lines = map(lambda x: '{}{}{}'.format(x['key'],
                                             seperator,
                                             x['value']), valid)
    output = '\n'.join(to_lines)
    return {'output': output,
            'invalid': invalid}

def _join_prefix_key(item):
    prefix = item['prefix']
    key = item['key']
    if prefix:
        item['prefix'] = None
        item['key'] = prefix+key
    return item

def serialize_shell(items):
    v_keys = filter_both(_keyfile_valid_key, items)
    v_prefixes = filter_both(lambda x: x['prefix'] == None, v_keys['match'])
    accepted_prefixes = filter_both(_valid_prefix, v_prefixes['no_match'])
    good_prefixes = map(join_prefix, accepted_prefixes['match'])
    valid = chain(v_prefixes['match'], good_prefixes)
    invalid = chain(v_keys['no_match'], accepted_prefixes['no_match'])
    to_lines = map(lambda x: 'export {}={}'.format(x['key'],
                                                   x['value']), valid)
    output = '\n'.join(to_lines)
    return {'output': output,
            'invalid': invalid}    


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
        f.write(result['output'])
    return result
    
    
