import yaml
from lookups import BaseLookup

class CloudFormationTemplate(BaseLookup):
    allowed_prefixes = ['Outputs', 'Parameters']
    def __init__(self, cfn_filename):
        self.body = self._read_template(cfn_filename)

    def _read_template(self, cfn_filename):
        self.cfn_filename = cfn_filename
        with open(cfn_filename) as f:
            template_body = f.read()
        no_refs = template_body.replace('!', '')
        return yaml.load(no_refs)

    def _valid_prefix(self, prefix):
        if prefix in self.allowed_prefixes:
            return prefix
        return None
    
    def list_prefixes(self):
        return self.allowed_prefixes
        
    def get(self, key, prefix=None):
        try:
            p = self._valid_prefix(prefix)
            n = self.body[prefix][key]
            value = key
        except LookupError:
            value = None
        result = {'key': key,
                  'value': value,
                  'prefix': prefix}
        try:
            result['Description'] = n['Description']
        except (UnboundLocalError, LookupError):
            pass

        return result

    def list_keys(self, prefix=None):
        try:
            p = self._valid_prefix(prefix)
            return {'prefix': prefix,
                    'keys': list(self.body[p].keys())}
        except (LookupError, TypeError):
            return {'prefix': prefix,
                    'keys': []}

    def get_all(self, prefix=None):
        '''
        Return all available key/value pairs from the given lookup source
        Has the option to return items for a given prefix as well
        '''
        if prefix:
            p = self._valid_prefix(prefix)
            if p:
                lookup = [p]
            else:
                return []
        else:
            lookup = self.list_prefixes()
        items = []
        for prefix in lookup:
            keys = self.list_keys(prefix)['keys']
            items.extend([self.get(key=key, prefix=prefix) for key in keys])
        return items
                

