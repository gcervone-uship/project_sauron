from itertools import chain
from utils import filter_both, not_none

class SauronPrimitive(object):
    def __repr__(self):
        rep = {x: getattr(self, x) for x in self.__slots__}
        return '{} {}'.format(self.__class__.__name__, rep)
    def NOiter__(self):
        '''
        Add on an __iter__ method that gives us a single item iterator
        of ourself. This makes it easier for writing things that only have to deal with a single item
        '''
        print('pretended to be an iterable')
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
class ResultList(list): pass

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

def drop_prefix(item):
    item['prefix'] = None
    return Result(result=item)

def make_valid(item):
    return Result(result=item)

def make_invalid(item):
    return Result(invalid=item)

def NOem_action(pred, items,
                key_filter = make_valid,
                prefix_filter = make_valid):
    v_prefix = filter_both(prefix_filter, items)
    v_keys = filter_both(key_filter, v_prefix['match'])
    res = map(pred, v_keys['match'])
    results = chain(res, v_prefix['no_match'], v_keys['no_match'])
    return results

def item_action(pred, items, filters=[]):
    per_item = lambda elem: reduce(lambda l, r: action_on_result(r, l), filters, elem)
    return map(per_item, items)

def action_on_result(pred, res):
    #print('\nAction: {}\nitem: {}'.format(pred, res))
    if type(res) == Result:
        if res.result:
            action_result = pred(res.result)
            #print('Action Result on Result: {}'.format(action_result))
            return action_result
        return res
    if type(res) == Item:
        action_result = pred(res)
        #print('Action Result on Item: {}'.format(action_result))
        return action_result
    #print("Pretty sure we shouldn't be here\n")
    return res
    
    
