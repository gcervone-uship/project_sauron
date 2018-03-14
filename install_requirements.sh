#!/bin/bash

# Install requirements 

if [ $(whoami) != 'root' ]
then
  echo 'Please run as root.'
  exit 1
fi

if [ -z $(which python3) ]
then 
  yum install -y python36
fi

if [ -z $(which pip-3.6) ]
then
  yum install -y python36-pip
fi

echo 'All requirements are installed...'
echo 'installing required modules...'

pip-3.6 install -r env_builder/requirements.txt --user
pip-3.6 install -r deploy/requirements.txt --user
