#!/usr/bin/env bash

logName=$(date '+%Y-%m-%d_%H-%M-%S');

mkdir -p /var/log/nmcp

export PYTHONPATH=$PWD

python nmcp/precomputed_worker.py -u $GRAPHQL_URL -a $SERVER_AUTHENTICATION_KEY -o $PRECOMPUTED_OUTPUT  >> /var/log/nmcp/nmcp-precomputed-${logName}.log 2>&1
