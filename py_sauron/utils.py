from itertools import tee, filterfalse

def filter_both(pred, items):
    valid, invalid = tee(items)
    return {'match': filter(pred, valid),
            'no_match': filterfalse(pred, invalid)}

def not_none(item):
    if item == None:
        return False
    else:
        return True
