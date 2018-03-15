#!/bin/bash

# Install requirements 

echo 'installing required modules...'

pip-3.6 install -r env_builder/requirements.txt
pip-3.6 install -r deploy/requirements.txt
