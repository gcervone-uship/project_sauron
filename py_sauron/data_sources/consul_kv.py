from consul import Consul, ConsulException
import socket

from primitives.item_primitives import join_prefix, item_action, Result, Item, split_by_sep

CONSUL_SEP = '/'

def is_consul_prefix(item):
    '''
    Verify that the item's prefix is appropriate for consul
    return a valid result if it is, return an invalid Result if it isn't
    '''
    prefix = item.prefix
    if prefix == None:
        return Result(result = item)
    if prefix[0] != '/':
        return Result(result = item)
    return Result(invalid = item)

def _put_consul(item, conn):
    n_item = join_prefix(item, '/')
    try:
        r = conn.kv.put(n_item.key, item.value)
        if r != None:
            return Result(result=item)
        else:
            return Result(invalid=item)
    except (ConsulException, socket.error) as e:
        return Result(invalid=item,
                      exception=e)

def _get_consul(item, conn, recurse=False):
    '''
    If recurse is set, we will return all items matching this item's prefix
    We may want validation to ensure we can't dump all of consul's key/value pairs
    '''
    if recurse and item.prefix != None:
        c_key = item.prefix
    elif recurse and item.prefix == None:
        return []
    else:
        c_key = join_prefix(item, CONSUL_SEP).key
    try:
        raw = conn.kv.get(c_key, recurse=recurse)
    except (ConsulException, socket.error) as e:
        return Result(invalid=item,
                      exception=e)
    
    def __handle_result(__res):
        '''
        Small convenience function for taking the Value of a result and decoding it
        '''
        _res = Item(key=__res['Key'],
                    value = __res['Value'].decode())
        return _res
    if raw[1]:
        if recurse:
            r_items = map(__handle_result, raw[1])
        else:
            r_items = __handle_result(raw[1])
        split_by_consul = lambda x: split_by_sep(x, CONSUL_SEP)
        result = map(split_by_consul, r_items)
        return Result(result)
    return Result(invalid=item)

def get_consul_by_prefix(s_item, conn=Consul()):
    '''
    Query consul recursively to get anything matching the items's prefix
    '''
    get = lambda x: _get_consul(x, conn, recurse=True)
    return get(s_item)

def get_consul(s_item, conn=Consul()):
    '''
    Query consul for the prefix and key of the provided item
    '''
    get = lambda x: _get_consul(x, conn)
    return get(s_item)

def put_consul(s_item, conn=Consul()):
    '''
    Write an item to consul
    '''
    put = lambda x: _put_consul(x, conn)
    return put(s_item)
        
