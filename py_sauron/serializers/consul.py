from itertools import tee, chain, filterfalse

from consul import Consul, ConsulException

def filter_both(pred, items):
    valid, invalid = tee(items)
    return {'match': filter(pred, valid),
            'no_match': filterfalse(pred, invalid)}

def _valid_prefix(item):
    prefix = item['prefix']
    if prefix == None:
        return item
    if prefix[0] != '/':
        return item
    return None

def _handle_prefix(item):
    prefix = item['prefix']
    key = item['key']
    if prefix:
        item['prefix'] = None
        item['key'] = prefix+key
    return item

def _put_consul(item, conn):
    try:
        result = conn.kv.put(item['key'], item['value'])
        exception = None
    except ConsulException as e:
        result = False
        exception = e
    return {'result': result,
            'exception': exception,
            'item': item}

def _get_consul(item, conn):
    n_item = _handle_prefix(item)
    try:
        raw = conn.kv.get(item['key'])
        exception = None
    except ConsulException as e:
        raw = None
        result = None
        exception = e
    if raw:
        result = raw['Value'].decode()
    else:
        result = None
    return {'result': result,
            'exception': exception,
            'item': item,
            'raw': raw}

def _consul_action(f, items):
    v_prefixes = filter_both(_valid_prefix, items)
    h_items = map(_handle_prefix, v_prefixes['match'])
    raw = map(f, h_items)
    results = filter_both(lambda x: x['result'], raw)
    # Return the results as lists to make sure we consume all our iterators
    # Otherwise the caller would need to consume them.
    # This is fine for reading, but since we might be writing, we probably want to make sure
    # Everythning gets written out before we return.
    return {'results': list(results['match']),
            'failed': list(results['no_match']),
            'invalid': list(v_prefixes['no_match'])}

def lookup_consul(items, conn=Consul()):
    get = lambda x: _get_consul(x, conn)
    return _consul_action(get, items)

def serialize_consul(items, conn=Consul()):
    put = lambda x: _put_consul(x, conn)
    return _consul_action(get, items)

    
        
