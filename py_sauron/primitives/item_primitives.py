from itertools import chain
from utils import filter_both, not_none

class SauronPrimitive(object):
    def __repr__(self):
        rep = {x: getattr(self, x) for x in self.__slots__}
        return '{} {}'.format(self.__class__.__name__, rep)
    def __iter__(self):
        '''
        Add on an __iter__ method that gives us a single item iterator
        of ourself. This makes it easier for writing things that only have to deal with a single item
        This is mainly for being able to handle results and invalids without having to worry about if they
        are a single item or multiple items
        '''
        yield self
    
class Result(SauronPrimitive):
    '''
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
    '''
    __slots__ = ['result', 'invalid', 'raw', 'exception', 'retry', 'output']
    def __init__(self, result=None, invalid=None, raw=None, exception=None, retry=False, output=None):
        self.result = result
        self.invalid = invalid
        self.raw = raw
        self.exception = exception
        self.retry = False
        self.output = output


class Item(SauronPrimitive):
    __slots__ = ['key', 'value', 'prefix', 'extra']
    def __init__(self, key=None, value=None, prefix=None, extra=None):
        self.key = key
        self.value = value
        self.prefix = prefix
        self.extra = extra
    def clone(self,key=None, value=None, prefix=None, extra=None):
        '''
        Make a new copy of the item allowing for updated attributes
        '''
        cl = self.__class__
        if key:
            n_key = key
        else:
            n_key = n_key = self.key
        if value:
            n_value = value
        else:
            n_value = self.value
        if prefix:
            n_prefix = prefix
        else:
            n_prefix = self.prefix
        if extra:
            n_extra = extra
        else:
            n_extra = self.extra
            
        return cl(key = n_key,
                  value = n_value,
                  prefix = n_prefix,
                  extra = n_extra)
        

class ItemList(list): pass

def join_prefix(item, sep=''):
    prefix = item.prefix
    key = item.key
    if prefix != None:
        n_item = item.clone(key= '{}{}{}'.format(prefix, sep, key), prefix=None)
        return Result(result = n_item)
    return Result(result=item)

def split_prefix(item, prefix, sep=''):
    '''
    Take an item with a None prefix, a prefix, and optionally a seperator
    '''
    left = prefix+sep
    if item.prefix != None:
        return Result(invalid=item)
    if not item.prefix.startswith(start):
        return Result(invalid=item)
    n_key = item.key.lstrip(left)
    n_item = item.clone(key=n_key, prefix=prefix)
    return Result(result=n_item)

def drop_prefix(s_item):
    s_item['prefix'] = None
    return Result(result=s_item)

def make_valid(s_item):
    return Result(result=s_item)

def make_invalid(s_item):
    return Result(invalid=s_item)

def item_action(pred, s_items, actions=[make_valid]):
    per_item = lambda elem: reduce(lambda l, r: action_on_result(r, l), actions, elem)
    return map(per_item, s_items)

def action_on_result(pred, ob):
    if type(ob) == Result:
        if ob.result:
            return pred(ob.result)
        return ob
    if type(ob) == Item:
        return  pred(ob)
    # Just drop it through if we don't specifically know how to handle it.
    return ob
