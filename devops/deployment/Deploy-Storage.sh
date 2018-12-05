#!/bin/bash

# Need commands to fail early.
set -e
set -o pipefail

if ! [ -x "$(command -v az)" ]; then
    echo "Error Azure CLI not installed."; >&2
    echo "See: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli?view=azure-cli-latest to install Azure CLI"; >&2
    exit 1
fi

if [ -z "$RESOURCE_GROUP" ]; then
    echo "Need to set resource group in the environment."; >&2
    exit 1
fi

if [ -z "$STORAGE_NAME" ]; then
    echo "Need to set storage name in the environment."; >&2
    exit 1
fi

#A conditional to choose whether or not to redploy the storage account if it already exists
REDEPLOY_AZURE_STORAGE=${REDEPLOY_STORAGE:="true"}
if $REDEPLOY_AZURE_STORAGE; then
    #First see if the storage account exists. 
    storage_query_result=$(az storage account list -g $RESOURCE_GROUP --query "[?name=='$PROJECT_STORAGE_ACCOUNT'].name")
    if [[ $storage_query_result =~ $STORAGE_NAME ]];
    then
        echo "Storage account $STORAGE_NAME already exists. Removing..."
        az storage account delete -g $RESOURCE_GROUP -n $STORAGE_NAME -y
    fi
fi

echo "Creating Storage Account"

az storage account create --resource-group $RESOURCE_GROUP --name $STORAGE_NAME --sku Standard_LRS
STORAGE_KEY=$(az storage account keys list -n $STORAGE_NAME --resource-group $RESOURCE_GROUP  --query [0].value)

echo "Creating Temporary Storage Container"
az storage container create -n $STORAGE_TEMP_CONTAINER --account-key $STORAGE_KEY --account-name $STORAGE_NAME --public-access container

echo "Creating Permanent Storage Container"
az storage container create -n $STORAGE_PERM_CONTAINER --account-key $STORAGE_KEY --account-name $STORAGE_NAME --public-access container

echo "Creating an onboarding queue"
az storage queue create -n onboardqueue --account-key $STORAGE_KEY --account-name $STORAGE_NAME

echo "Done!"