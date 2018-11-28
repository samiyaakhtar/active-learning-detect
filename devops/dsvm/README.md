# Setting up an Azure DSVM for Active Learning

This document will explain how to deploy an Azure DSVM and set up the environment for Active Learning.

## Deployment

Create an SSH Key on your local machine. The following will create a key in your ~/.ssh/act-learn-key location.

```sh
$ ssh-keygen -f ~/.ssh/act-learn-key -t rsa -b 2048
```

Secondly edit the environment variables in the [dsvm_config.sh](config/dsvm_config.sh) script with your own values. For instance:

<pre>
RESOURCE_GROUP=<b>MyAzureResourceGroup</b>
# VM config
VM_SKU=Standard_NC6 #Make sure VM SKU is available in your resource group's region 
VM_IMAGE=microsoft-ads:linux-data-science-vm-ubuntu:linuxdsvmubuntu:latest
VM_DNS_NAME=<b>mytestdns</b>
VM_NAME=<b>myvmname</b>
VM_ADMIN_USER=<b>johndoe</b>
VM_SSH_KEY=~/.ssh/act-learn-key.pub
</pre>

Lastly execute the deploy_dsvm.sh with your edited config file as a parameter. Note that the Azure CLI is required. Install [here](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli) is needed.

```sh
$ sh deploy_dsvm.sh config/dsvm_config.sh
```

## Environment Setup 
We provide a module that will copy over a shell script to your DSVM and execute the shell script to setup an active learning environment.

We requirement that your ssh key be added to the SSH agent. You can do so my using the **_ssh-add_** command

```sh
$ ssh-add -K ~/.ssh/act-learn-key
```

To copy and execute the shells script use the following command

```sh
$ python setup-tensorflow.py --host admin@127.0.0.1 -k ~/.ssh/act-learn-key -s setup-tensorflow.sh
```

Note that in the host argument **_admin_**@127.0.0.1 section is the DSVM Admin name and admin@**_127.0.0.1_** is the IP address of the DSVM.