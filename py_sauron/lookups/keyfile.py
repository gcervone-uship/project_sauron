from itertools import chain

from lookups import BaseLookup
from utils import filter_both, not_null

class KeyFileLookup(BaseLookup):
    default_sep = '='
    def __init__(self, keyfile,
                 seperator = default_sep,
                 ignore_bad_lines=False,
                 allow_empty_values=False):
        self.seperator = seperator
        # Pull everything into a list so we don't have to worry about the file changing
        self.raw_lines = list(self._load(keyfile))

    def _load(self, keyfile):
        try:
            with open(keyfile) as f:
                lines = f.readlines()
                result = map(lambda x: x.strip('\n'), lines)
            return result
        except OSError:
            return []
    def _valid_key(self, key):
        return key
    
    def _valid_value(self, value):
        if value == None:
            if self.allow_empty_values:
                return ''
            else:
                return None
        return value

    def _split_line(self, line):
        spl = line.split(self.seperator)
        if len(spl) == 2:
            key = self._valid_key(spl[0])
            value = self._valid_value(spl[0])
        elif len(spl) == 1:
            key = spl[0]
            value = None
        else:
            key = None
            value = None
        return {'key': key,
                'value': value}

    def _items(self, raw_lines):
        lines = map(self._split_line, raw_lines)
        v_keys = filter_both(lambda x: self._valid_key(x['key']), lines)
        v_values = filter_both(lambda x: self._valid_value(x['value']), v_keys['match'])
        invalid = chain(v_keys['no_match'], v_values['no_match'])
        return {'results': v_values,
                'invalid': invalid}
    
    def items(self):
        items = self._items(self.raw_lines)
        invalid = list(items['invalid'])
        valid = list(items['valid'])
        return valid


