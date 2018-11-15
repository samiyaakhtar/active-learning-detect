#!/bin/bash

# System config 
RESOURCE_GROUP=jmsrg1

# VM config
VM_SKU=Standard_NC6
VM_IMAGE=microsoft-ads:linux-data-science-vm-ubuntu:linuxdsvmubuntu:latest
VM_DNS_NAME=jmsactlrnvm
VM_NAME=jmsactlrnvm
VM_ADMIN_USER=vmadmin
VM_SSH_KEY=~/.ssh/act-learn-key.pub