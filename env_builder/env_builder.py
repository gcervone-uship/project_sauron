#!/usr/bin/env python3
import logging
import argparse
import os
import sys
import re

from consul import Consul

def get_cli_opts():
    description = 'Build a .env file for Docker Compose'
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument('-t', '--type',
                        required=True,
                        help='Type of build, ex: local jenkins etc',
                        choices=['local', 'environment', 'consul'],
    )

    parser.add_argument('-k', '--key',
                        required=True,
                        help='Example Key  file',
                        type=argparse.FileType('r'))

    parser.add_argument('-d', '--destination',
                        default='/dev/stdout',
                        help='Output Destination',
                        type=argparse.FileType('w'))

    parser.add_argument('-p', '--prefix',
                        required=False,
                        default='',
                        help='Prefix for environment variables or consul path. Ex: "bamboo_" or "dev/"')

    return parser.parse_args()


def key_parse_lines(lines, sep='='):
    '''
    Ensure that each line meets our required formatting
    This expects every line to contain a properly formatted key value pair
    '''
    allowed_characters = re.compile(r'^[0-9A-Z\_]+$')
    pairs = {}
    for line in lines:
        pair = line.split(sep)
        if len(pair) != 2:
            raise KeyError('Error parsing line:\n{}'.format(line))
        key_allowed = allowed_characters.findall(pair[0])
        if len(key_allowed) != 1:
            raise KeyError('Invalid Characters in key: {}'.format(pair[0]))
        if pair[0] in pairs.keys():
            if pairs[pair[0]] == pair[1]:
                logging.warning('Duplicate Key/Value: {} {}'.format(
                    pair[0], pair[1]))
            else:
                raise ValueError('Conflicting values for {}:\n{}\n{}'.format(
                    pair[0],
                    pair[1],
                    pairs[pair[0]]))
        pairs[pair[0]] = pair[1]
    return pairs

def read_keyfile(infile, sep='='):
    '''
    Convenience Function to call readlines before parsing the lines
    '''
    lines = [x.strip('\n') for x in infile.readlines()]
    return key_parse_lines(lines, sep)


def serialize_env(env_items, sep='=', escaping=False):
    '''
    Take a dictionary of env items and format it with our desired separators
    '''
    w_seps = ['{}{}{}'.format(k, sep, v) for k,v in env_items.items()]
    return '\n'.join(w_seps)

def lookup_env_var(key):
    if key in os.environ:
        val = os.environ[key]
        return (key, val)
    else:
        raise KeyError('Key {} doesn\'t appear to be exported'.format(key))

def get_from_env(env_items, prefix=''):
    '''
    Take a list or dictionary containing all of our required keys
    along with an optional prefix, and look them up in our environment variables
    '''
    keys = ['{}{}'.format(prefix, x) for x in env_items]
    not_in_env = [x for x in keys if x not in os.environ]
    if len(not_in_env) > 0:
        error_msg = 'The following items are missing from our environment: {}'
        raise KeyError(error_msg.format(not_in_env))
    pairs = [(k, os.environ[prefix+k]) for k in env_items]
    return dict(pairs)
    

def get_keys_consul(keys, prefix='', **overrides):
    conn = Consul(**overrides)
    if len(prefix) > 0:
        prefix = '{}/'.format(prefix.strip('/'))
    items = {}
    for key in keys:
        index, data = conn.kv.get(prefix+key)
        if data:
            if data['Value'] != None:
                items[key] = data['Value'].decode()
    missing = [x for x in keys if x not in items]
    if len(missing) > 0:
        raise KeyError('The following items are missing: {}'.format(missing))
    return items



if __name__ == '__main__':
    args = get_cli_opts()
    items = read_keyfile(args.key)
    if args.type == 'local':
        result = items
    elif args.type == 'environment':
        result = get_from_env(items, args.prefix)
    elif args.type == 'consul':
        result = get_keys_consul(items, args.prefix)
    args.destination.writelines(serialize_env(result)+'\n')
    
