import os
import logging
import json
import azure.functions as func
import paramiko

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    ssh.connect('<host-ip>', username='vmadmin', key_filename='./train/act-learn-key')

    stdin, stdout, stderr = ssh.exec_command('ls')
    logging.info(stdout.readlines())
    ssh.close()

    # setup response object
    headers = {
        "content-type": "application/json"
    }
    return func.HttpResponse(
        status_code=200,
        headers=headers
    )
