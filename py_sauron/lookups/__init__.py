class BaseLookup(object):
    def get(self, key, prefix=None): raise NotImplemented
    def get_many(self, keys, prefix=None): raise NotImplemented
    def list_keys(self, prefix=None): raise TypeError
    def _valid_key(self, key): return key
    def _valid_value(self, value): return value



