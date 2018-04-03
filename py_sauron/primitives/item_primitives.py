from itertools import groupby
from functools import reduce, wraps
from collections import defaultdict

from utils import filter_both

class SauronPrimitive(object):
    __slots__ = []
    """
    Base class for Sauron Objects. Mainly to turn things into iterables, and automatically generate
    a nice __repr__
    """
    def __repr__(self):
        rep = {x: getattr(self, x) for x in self.__slots__ if getattr(self, x)}
        return '{} {}'.format(self.__class__.__name__, rep)
    def __iter__(self):
        """
        Add on an __iter__ method that gives us a single item iterator
        of ourself. This makes it easier for writing things that only have to deal with a single item
        This is mainly for being able to handle results and invalids without having to worry about if they
        are a single item or multiple items
        """
        yield self

class Result(SauronPrimitive):
    """
    Result objects represent the state of an action taken on an item
    It uses the following attributes:
      * result (successfully handled items)
        This represents items that were handled successfully,
        the results of a successful change to an item
        or the results of a successful lookup
      * invalid (failure)
        This represents items that were not handled successfully
        or failed lookups
      * raw (debugging aid)
        the raw attribute is available for debugging, and is intended to be used for placing raw response objects
      * exception
        The exception encountered while handling a request
      * retry
        Can the failed request be retried at a later time
        For example, you might want to retry if you recieved a socket error while trying to connect to consul
      * output
        The formatted output of an action. For example, serializing something to json or yaml.
    """
    __slots__ = ['result', 'invalid', 'raw', 'exception', 'retry', 'output']
    def __init__(self, result=None, invalid=None, raw=None, exception=None, retry=False, output=None):
        self.result = result
        self.invalid = invalid
        self.raw = raw
        self.exception = exception
        self.retry = retry
        self.output = output


class Item(SauronPrimitive):
    """
    Sauron Item Primitive. This is the fundamental class that will be utilized in py_sauron
    """
    __slots__ = ['key', 'value', 'prefix', 'extra']
    def __init__(self, key=None, value=None, prefix=None, extra=None):
        self.key = key
        self.value = value
        self.prefix = prefix
        self.extra = extra
    def __eq__(self, other):
        return (self.prefix, self.key, self.value) == (other.prefix, other.key, other.value)
    def __ne__(self, other):
        return not self == other
    def __lt__(self, other):
        return (self.prefix, self.key, self.value) < (other.prefix, other.key, other.value)
    def __gt__(self, other):
        return (self.prefix, self.key, self.value) > (other.prefix, other.key, other.value)
    def __hash__(self):
        return hash((self.prefix, self.key, self.value))
    def clone(self, key=None, value=None, prefix=None, extra=None, drop=[]):
        """
        Make a new copy of the item allowing for updated attributes
        We can also pass a list or string with an item to drop (Set to None in the new object)
        """
        clone = self.__class__
        if key:
            n_key = key
        elif 'key' in drop:
            n_key = None
        else:
            n_key = n_key = self.key
        if value:
            n_value = value
        elif 'value' in drop:
            n_value = None
        else:
            n_value = self.value
        if prefix:
            n_prefix = prefix
        elif 'prefix' in drop:
            n_prefix = None
        else:
            n_prefix = self.prefix
        if extra:
            n_extra = extra
        elif 'extra' in 'drop':
            n_extra = None
        else:
            n_extra = self.extra

        return clone(key=n_key,
                     value=n_value,
                     prefix=n_prefix,
                     extra=n_extra)

def accept_none_item(func):
    @wraps(func)
    def wrapped(s_item, *args, **kwargs):
        if s_item is None:
            return func(Item(), *args, **kwargs)
        return func(s_item, *args, **kwargs)
    return wrapped

def accept_none_items(func):
    @wraps(func)
    def wrapped(s_items, *args, **kwargs):
        if s_items is None:
            return func([], *args, **kwargs)
        return func(s_items, *args, **kwargs)
    return wrapped

@accept_none_item
def join_prefix(s_item, sep=''):
    prefix = s_item.prefix
    key = s_item.key
    if prefix != None:
        n_item = s_item.clone(key='{}{}{}'.format(prefix, sep, key), prefix=None)
    else:
        n_item = s_item
    return n_item

@accept_none_item
def split_prefix(s_item, prefix, sep=''):
    """
    Take an item with a None prefix, a prefix, and optionally a seperator
    """
    left = prefix+sep
    if s_item.prefix != None:
        return Result(invalid=s_item)
    if not s_item.prefix.startswith(left):
        return Result(invalid=s_item)
    n_key = s_item.key.lstrip(left)
    n_item = s_item.clone(key=n_key, prefix=prefix)
    return n_item

@accept_none_item
def split_by_sep(s_item, sep):
    """
    Take an item with an empty prefix and a seperator, and generate a prefix
    If a seperator is repeated, only use the final section as the key, the rest will be joined back together
    with the seperator to form the prefix
    """
    key = s_item.key
    prefix = s_item.prefix
    if prefix is not None:
        return Result(invalid=s_item)
    spl = key.split(sep)
    n_key = spl[-1]
    n_prefix = sep.join(spl[:-1])
    n_item = s_item.clone(key=n_key,
                          prefix=n_prefix)
    return n_item

@accept_none_item
def new_prefix(s_item, prefix):
    n_item = s_item.clone(prefix=prefix)
    return n_item

@accept_none_item
def drop_prefix(s_item):
    n_item = s_item.clone(drop='prefix')
    return n_item

@accept_none_item
def drop_value(s_item):
    return s_item.clone(drop='value')

@accept_none_item
def make_valid(s_item):
    return Result(result=s_item)

@accept_none_item
def make_invalid(s_item):
    return Result(invalid=s_item)

@accept_none_items
def item_action(s_items, actions=[make_valid]):
    per_item = lambda elem: reduce(lambda l, r: action_on_result(r, l), actions, elem)
    return map(per_item, s_items)

def action_on_result(pred, s_obj):
    if isinstance(s_obj, Result):
        if s_obj.result:
            return pred(s_obj.result)
        return s_obj
    if isinstance(s_obj, Item):
        return  pred(s_obj)
    # Just drop it through if we don't specifically know how to handle it.
    return s_obj

@accept_none_items
def get_by_prefix(s_items, prefix):
    result, invalid = filter_both(lambda x: x.prefix == prefix, s_items)
    return Result(result=result,
                  invalid=invalid)

@accept_none_items
def dedup_items(s_items):
    return map(lambda x: x[0], groupby(s_items))

@accept_none_items
def dedup_prefix_keys(s_items, invalid_fatal=True):
    valid = []
    invalid = []
    dedupped = dedup_items(s_items)
    item_groups = {k: list(g) for k, g in groupby(dedupped, key=lambda x: (x.prefix, x.key))}
    for prefix, key in item_groups.items():
        if key:
            valid.extend(key)
        else:
            invalid.extend(key)
    if invalid and invalid_fatal:
        raise KeyError('Overlapping Key Value Pairs: {}'.format(invalid))
    return Result(result=valid,
                  invalid=invalid)

def fill_values(required_items, source_items, invalid_fatal=True):
    """
    Make a dictionary with values of None out of our required items
    go through the source items and fill in all our keys
    This will give us a dictionary containing our default values
    Now we just need to iterate over our known items, and overwrite any defaults
    Once we've got the resulting dictionary, we can check to make sure we don't have any
    values of none remaining
    """
    result = defaultdict(lambda x: None)
    for r_item in required_items:
        result[r_item.key] = r_item.value
    s_item_dict = {}
    for src_item in source_items:
        src_key = src_item.key
        src_value = src_item.value
        if src_key in result and src_value != None:
            result[src_key] = src_value

    base_valid = []
    base_invalid = []
    for key, value in result.items():
        if value:
            base_valid.append(Item(key=key, value=value))
        else:
            base_invalid.append(Item(key=key, value=value))
    if base_invalid == []:
        invalid = None
    else:
        if invalid_fatal:
            raise ValueError('Required Values Missing: {}'.format(base_invalid))
        invalid = base_invalid
    if base_valid == []:
        valid = None
    else:
        valid = base_valid
    return Result(result=valid,
                  invalid=invalid)

def inspector(ins):
    print('---Current: {}'.format(ins))
    return ins

@accept_none_items
def operate(s_items):
    return [x for x in s_items]
