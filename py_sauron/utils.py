"""
Assorted functions for clarifying or simplifying operations
"""

from itertools import tee, filterfalse
from collections import namedtuple

def filter_both(pred, items):
    valid, invalid = tee(items)
    filtered = namedtuple('Filtered', ['match', 'no_match'])
    return filtered(filter(pred, valid), filterfalse(pred, invalid))
