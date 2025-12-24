#!/usr/bin/env bash

# Start service(s) that are not typically under local development (e.g., databases), but are required to run and test services that may be under development.

if [ -z "NMCP_COMPOSE_PROJECT" ]; then
    export NMCP_COMPOSE_PROJECT="nmcp"
fi

docker compose -p ${NMCP_COMPOSE_PROJECT} up
