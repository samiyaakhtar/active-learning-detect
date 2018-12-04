#!/bin/bash
set -x

# Check if we are in a virutal env (needed to deploy functions, database)
if [ -z "$VIRTUAL_ENV" ]; then
    echo "A virtual environment using Python 3.6 is needed.  Please make sure Python 3.6"
    echo "is installed and the virtual environment is created with the appropriate command"
    echo "which would be something like: python3.6 -m venv <path to venv>"
    echo ""
    echo "You will then need to activate the venv, which on *nix based systems would be:"
    echo "  source <path to venv>/bin/activate"
    exit 1
fi

# Check if the python version is 3.6
#python --version | awk '{print $2}' | grep "^3.6" >& /dev/null
#if [ "$?" -ne "0" ]; then
#    echo "Python version 3.6.x is required."
#    exit 1
#fi

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
. $1

# Install reuired python modules
pip install -r ../../requirements.txt

# Setup database
DATABASE_USERNAME_AT_HOST="$DATABASE_USERNAME@$DATABASE_SERVER_NAME"
. ./Deploy-Postgres-DB.sh $RESOURCE_GROUP $DATABASE_SERVER_NAME "$DATABASE_USERNAME" $DATABASE_PASSWORD
if [ "$?" -ne 0 ]; then
    echo "Unable to setup database"
    exit 1
fi

# Setup database schema
DB_HOST_FULL_NAME="$DATABASE_SERVER_NAME"".postgres.database.azure.com"
(cd ../../db && export DB_HOST=$DB_HOST_FULL_NAME && export DB_USER="$DATABASE_USERNAME_AT_HOST" && export DB_PASS=$DATABASE_PASSWORD && ./install-db-resources.py $DATABASE_NAME)

# Setup app insights
. ./Deploy-AppInsights.sh $RESOURCE_GROUP $APPINSIGHTS_NAME
if [ "$?" -ne 0 ]; then
    echo "Unable to setup app insights"
    exit 1
fi

# Setup storage assets needed by functions
export RESOURCE_GROUP=$RESOURCE_GROUP
export STORAGE_NAME=$PROJECT_STORAGE_ACCOUNT
export STORAGE_TEMP_CONTAINER=$PROJECT_STORAGE_TEMP_CONTAINER
export STORAGE_PERM_CONTAINER=$PROJECT_STORAGE_PERM_CONTAINER
./Deploy-Storage.sh
if [ "$?" -ne 0 ]; then
    echo "Unable to create storage accounts and containers"
    exit 1
fi

STORAGE_CONNECTION_STRING=$(az storage account show-connection-string -n $PROJECT_STORAGE_ACCOUNT -g $RESOURCE_GROUP --query "connectionString")

# Setup azure python function
PROJECT_STORAGE_ACCOUNT_KEY=$(az storage account keys list -n $PROJECT_STORAGE_ACCOUNT --query [0].value --resource-group $RESOURCE_GROUP)
. ./Deploy-Python-Functions-App.sh \
        $RESOURCE_GROUP \
        $FUNCTION_STORAGE_ACCOUNT \
        $FUNCTION_APP_NAME \
        $APPINSIGHTS_NAME \
        $PROJECT_STORAGE_ACCOUNT \
        $PROJECT_STORAGE_ACCOUNT_KEY \
        $PROJECT_STORAGE_TEMP_CONTAINER \
        $PROJECT_STORAGE_PERM_CONTAINER \
        $DB_HOST_FULL_NAME \
        $DATABASE_USERNAME_AT_HOST \
        $DATABASE_PASSWORD \
        $DATABASE_NAME \
        $STORAGE_CONNECTION_STRING
if [ "$?" -ne 0 ]; then
    echo "Unable to setup app insights"
    exit 1
fi

. ./Deploy-Pipeline-Functions.sh $FUNCTION_APP_NAME ../../functions/pipeline
if [ "$?" -ne 0 ]; then
    echo "Unable to deploy pipeline functions"
    exit 1
fi