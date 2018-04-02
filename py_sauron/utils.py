from itertools import tee, filterfalse
from collections import namedtuple
"""
Assorted functions for clarifying or simplifying operations
"""



def filter_both(pred, items):
    valid, invalid = tee(items)
    Filtered = namedtuple('Filtered', ['match', 'no_match'])
    return Filtered(filter(pred, valid), filterfalse(pred, invalid))

def not_none(item):
    if item is None:
        return False
    else:
        return True
