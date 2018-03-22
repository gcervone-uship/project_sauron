from consul import Consul, ConsulException
import socket

from primitives.item_primitives import join_prefix, item_action, Result, Item

def is_consul_prefix(item):
    prefix = item.prefix
    if prefix == None:
        return Result(result = item)
    if prefix[0] != '/':
        return Result(result = item)
    return Result(invalid = item)

def _put_consul(item, conn):
    n_item = join_prefix(item, '/').result
    try:
        r = conn.kv.put(n_item.key, item.value)
        if r != None:
            return Result(result=item)
        else:
            return Result(invalid=item)
    except (ConsulException, socket.error) as e:
        return Result(invalid=item,
                      exception=e)

def _get_consul(item, conn):
    n_item = join_prefix(item, '/').result
    try:
        raw = conn.kv.get(n_item.key)
    except (ConsulException, socket.error) as e:
        return Result(invalid=item,
                      exception=e)
    if raw[1]:
        if raw[1]['Value']:
            value = raw[1]['Value'].decode()
        else:
            value = None
        result = Item(key = item.key,
                      value = value,
                      prefix = item.prefix)
        return Result(result = result,
                      raw = raw)
    else:
        return Result(invalid = item)

def get_consul(s_item, conn=Consul()):
    get = lambda x: _get_consul(x, conn)
    # return item_action(get, s_item, actions = [is_consul_prefix])
    return get(s_item)

def put_consul(s_item, conn=Consul()):
    put = lambda x: _put_consul(x, conn)
    # return item_action(put, s_item, actions = [is_consul_prefix])
    return put(s_item)
