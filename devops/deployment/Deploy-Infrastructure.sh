#!/bin/bash

# Check if any of the args are empty
if [ -z "$1" ]; then
    echo "Usage: 'sh $0 (Configuration file)'"
    exit 1
fi

# Is the config file present?
if [ ! -e "$1" ]; then
    echo "Configuration file does not exist."
    exit 1
fi

# Read configuration
. ./deployment_config.sh

# Setup database
. ./Deploy-Postgres-DB.sh $RESOURCE_GROUP $DATABASE_SERVER_NAME $DATABASE_USERNAME $DATABASE_PASSWORD
if [ "$?" -ne 0 ]; then
    echo "Unable to setup database"
    exit 1
fi

# Setup app insights
. ./Deploy-AppInsights.sh $RESOURCE_GROUP $APPINSIGHTS_NAME
if [ "$?" -ne 0 ]; then
    echo "Unable to setup app insights"
    exit 1
fi

# Setup azure python function
. ./Deploy-Python-Functions.sh $RESOURCE_GROUP $FUNCTION_STORAGE_ACCOUNT $FUNCTION_APP_NAME $APPINSIGHTS_NAME
if [ "$?" -ne 0 ]; then
    echo "Unable to setup app insights"
    exit 1
fi