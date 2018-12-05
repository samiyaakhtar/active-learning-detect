# Getting Starting With Active Learning Infrastructure

This directory contains several scripts to install the Active Learning infrastructure on to Azure. A more detailed look at database infrastructure deployment can be found [here](../../db/README.md) 

# Install Options
1. [Easy Install](#step1)
2. [Automated Install](#step2)

## Easy Install <a name="step1"></a>

The easiest way to get up and running is to manually update the _values_ of the config file [here](config/deployment_config.sh)

```
# Project configuration
RESOURCE_GROUP=my-resource-name
RESOURCE_LOCATION=westus
PROJECT_STORAGE_ACCOUNT=actlrnintstor
PROJECT_STORAGE_TEMP_CONTAINER=tempcont
PROJECT_STORAGE_PERM_CONTAINER=permcont

# Database config
DATABASE_NAME=mydatabasename
DATABASE_SERVER_NAME=mypostgresservername
DATABASE_USERNAME=actlrnadmin
DATABASE_PASSWORD=MyPassword2019

# AppInsights config
APPINSIGHTS_NAME=myappinsightsname

# Azure Function configuration
FUNCTION_STORAGE_ACCOUNT=actlrnintfuncstor
FUNCTION_APP_NAME=actlrnintegration
```

Next start a Python (3.5+) __virtual environment__ in the directory of deployment script (this directory). Next run the command below from the same directory:

```
. ./Deploy-Infrastructure config/deployment_config.sh
```

This command will deploy all the components necessary to accomplish tagging from scratch. 

## Automated Install <a name="step2"></a>

In deployment environments that rely on dynamic environment variables we allow our top level script to be run without config file. SET the environment variables defined [here](config/deployment_config.sh) in your Bash session

Start a Python (3.5+) __virtual environment__ in the directory of deployment script (this directory). Next run the command below from the same directory:

```
. ./Deploy-Infrastructure
```

# Azure Pipelines Continuous Deployment Example

TODO