#!/usr/bin/env python3
from argparse import ArgumentParser, ArgumentTypeError
from itertools import chain, repeat, starmap
import os
from pathlib import Path
import tarfile
from tempfile import TemporaryDirectory

import boto3

from primitives.item_primitives import Item
from plugins.cloudformation import get_cfn_stack
from plugins.consul_kv import get_consul


BUCKET_LOOKUP_KEY = 'S3Bucket'
WEBPACK_ACL = 'public-read'

def valid_path(path_string):
    new_path = Path(path_string).expanduser()

    if not new_path.exists():
        raise ArgumentTypeError('{} does not exist'.format(new_path))
    if not new_path.is_file():
        raise ArgumentTypeError('{} is not a file'.format(new_path))
    return new_path

def parse_args():
    description = 'Expand a webpack tarball and upload it to s3'
    parser = ArgumentParser(description=description)

    parser.add_argument('-s', '--source',
                        required=True,
                        type=valid_path)
    
    parser.add_argument('--source-prefix',
                        required=False,
                        default='',
                        help='Prefix to use with the source. (Ex: Directory inside a tarball)')

    parser.add_argument('--output-lookup',
                        required=False,
                        default='consul',
                        choices=['consul', 'param', 'cfn'],
                        help='Where look to see where the webpack will be written to')
    
    parser.add_argument('-d', '--output',
                        required=True,
                        help='Destination Location (Ex: Bucket to upload for param to or consul prefix to lookup for consul)')

    parser.add_argument('--output-prefix',
                        required=False,
                        default='',
                        help='Prefix to add when uploading file (Ex: Directory within an S3 bucket)')
                        
    return parser.parse_args()

def extract_tar(tarball_path, destination_action, subdirectory=''):
    """
    Destination Action needs to be a function that accepts a file path
    """
    with TemporaryDirectory() as temp_dir, tarfile.open(tarball_path) as tarball:
        assembled_path = Path(temp_dir, subdirectory).expanduser()
        def is_within_directory(directory, target):
            
            abs_directory = os.path.abspath(directory)
            abs_target = os.path.abspath(target)
        
            prefix = os.path.commonprefix([abs_directory, abs_target])
            
            return prefix == abs_directory
        
        def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
        
            for member in tar.getmembers():
                member_path = os.path.join(path, member.name)
                if not is_within_directory(path, member_path):
                    raise Exception("Attempted Path Traversal in Tar File")
        
            tar.extractall(path, members, numeric_owner=numeric_owner) 
            
        
        safe_extract(tarball, path=temp_dir)
        destination_action(assembled_path)

def make_key_from_path(path_name, key_prefix=None):
    new_path = Path(path_name)
    base_key = new_path.parts[-1]
    prefix = key_prefix.strip('/')
    if not prefix:
        key = base_key
    else:
        key = '{}/{}'.format(prefix, base_key)
    return (new_path, key)

def handle_dir(base_path):
    if base_path.is_file():
        return [base_path]
    elif base_path.is_dir():
        paths = starmap(Path, chain.from_iterable(map(lambda walked: zip(repeat(walked[0]), walked[2]), os.walk(base_path))))
        return map(lambda x: (x, os.path.relpath(x, base_path)), paths)
    return []

def make_s3_uploader(bucket_name, upload_prefix=None):
    s3 = boto3.resource('s3')
    dest_bucket = s3.Bucket(bucket_name)
    def upload(source_path):

        if upload_prefix is None:
            dest_prefix = ''
        else:
            dest_prefix = upload_prefix
        to_upload = handle_dir(source_path)
        path_with_keys = starmap(lambda l, r: (l, dest_prefix / Path(r)), to_upload)
        for path, key in path_with_keys:
            print('Uploading: {} to {} {}'.format(path, key, dest_bucket))
            dest_bucket.upload_file(str(path), str(key), ExtraArgs={'ACL': WEBPACK_ACL})
    return upload

def main():
    args = parse_args()
    output = args.output
    output_prefix = args.output_prefix
    output_lookup = args.output_lookup
    if output_lookup == 'consul':
        bucket_item = get_consul(Item(prefix=output, key=BUCKET_LOOKUP_KEY)).result
        if bucket_item is not None:
            output_bucket = [x.value for x in bucket_item][0]
            
        else:
            raise KeyError('Key {} not found in {}'.format(BUCKET_LOOKUP_KEY, output))
    elif output_lookup == 'cfn':
        cfn_lookup_results = get_cfn_stack(output).result
        output_bucket = [x.value for x in cfn_lookup_results if x.prefix == 'Outputs' and x.key == BUCKET_LOOKUP_KEY][0]
    else:
        output_bucket = output
        
    source = args.source
    source_prefix = args.source_prefix
    
    uploader = make_s3_uploader(output_bucket, output_prefix)
    extract_tar(source, uploader, source_prefix)

if __name__ == '__main__':
    main()
