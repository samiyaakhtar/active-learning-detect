import argparse
import json 
import requests
import os
import uuid
from azure.storage.blob import BlockBlobService, ContentSettings

storage_account_name = 'saakhtastoragetest'
storage_account_key = '<accountkey>'
storage_container_name = 'images'

# This file defines cli operations for onboarding new images onto the system.
# Example commands:
# python onboarding.py onboard -f ~/Documents/images/

# This takes a list of images, sends it to the blob store and gets image urls. 
# Sends the image urls to add them to db. 
def onboard(folder):
    blob_storage = BlockBlobService(account_name=storage_account_name, account_key=storage_account_key)
    uri = 'https://' + storage_container_name + '.blob.core.windows.net/' + storage_container_name + '/'

    for image in os.listdir(folder):
        if image.lower().endswith('.png') or image.lower().endswith('jpg') or image.lower().endswith('jpeg'):
            print("Uploading " + image)
            local_path=os.path.join(folder, image)
            print ("full path: " + local_path)

            blob_name = str(uuid.uuid4())
            # Upload the created file, use local_file_name for the blob name
            blob_storage.create_blob_from_path(storage_container_name, blob_name, local_path, content_settings=ContentSettings(content_type='image/png'))

    # List the blobs in the container
    # url of saved image: 
    # http://<storage-account-name>.blob.core.windows.net/<container-name>/<blob-name
    
    print("\nList blobs in the container")
    list = []
    generator = blob_storage.list_blobs(storage_container_name)
    for blob in generator:
        print("\t blob uri: " + uri + blob.name)
        list.append(uri + blob.name)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--folder', required=True)  
    parser.add_argument(
        'operation',
        choices=['onboard']
    )  
    args = parser.parse_args()

    operation = args.operation

    if operation == 'onboard':
        onboard(args.folder)