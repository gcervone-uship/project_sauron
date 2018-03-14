# Env Builder
Generate .env files for docker swarm

Help Output:
```
usage: env_builder.py [-h] -t {local,environment,consul} -k KEY
                      [-d DESTINATION] [-p PREFIX]
```

# Arguments

## Environment Type
Specifies the type of the environment. This will determine where the values are pulled from

 * -t
 * --type


### local
Passes the default values from the keyfile

### environment
Pulles the values from exported environment variables
This can be accompanied by the -p or --prefix flag for environment variables

For example, `-p bamboo_` can be used for pulling values in bamboo

### consul
Pulls the required values from a consul server. Consul defaults to connecting to localhost

The Consul library will read the following environment variables:

 * `CONSUL_HTTP_ADDR`
 * `CONSUL_HTTP_TOKEN`
 * `CONSUL_HTTP_SSL`
 * `CONSUL_HTTP_SSL_VERIFY`

The prefix option is also available for consul. The trailing slash for the prefix is optional:
For example `-p 'dev/demo'` or `-p 'dev/demo/' would both allow for pulling values such as `dev/demo/API_PORT` OR `dev/demo/API_PROTOCOL`


## Keyfile
Path to a keyfile. This file contains key value pairs

The keys are limited to capital letters, numbers, and underscores
The separator must be `=`
	
 * -k
 * --key

## Destination
Path to output the .env file to
This defaults to stdout
