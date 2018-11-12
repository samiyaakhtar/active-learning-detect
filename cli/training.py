import os
from azure.storage.blob import BlockBlobService, ContentSettings
from operations import (
    read_config,
    CONFIG_PATH,
    get_azure_storage_client
)

def train(config):
    # download all images
    download_images(config)


def download_images(config):
    blob_storage = get_azure_storage_client(config)
    generator = blob_storage.list_blobs(config.get("storage_container"))
    if not os.path.exists('images'):
        os.makedirs('images')
    for blob in generator:
        print(blob.name)
        blob_storage.get_blob_to_path(config.get("storage_container"),blob.name, "images/{}".format(blob.name))


if __name__ == "__main__":
    config = read_config(CONFIG_PATH)
    train(config)
