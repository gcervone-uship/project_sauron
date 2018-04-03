import os

from primitives.item_primitives import Item, Result, join_prefix, split_prefix


def lookup_env(s_item):
    """
    Lookup an item from the shell environment variables
    """
    s_prefix = s_item.prefix
    n_item = join_prefix(s_item, sep='_')
    environ_vars = os.environ
    env_key = n_item.key
    if env_key in environ_vars:
        env_value = environ_vars[env_key]
    else:
        env_value = None
    if s_prefix:
        d_item = split_prefix(Item(key=env_key, value=env_value), sep='_')
    else:
        d_item = Item(key=env_key, value=env_value)
    if d_item.value:
        return Result(result=d_item)
    return Result(invalid=d_item)
