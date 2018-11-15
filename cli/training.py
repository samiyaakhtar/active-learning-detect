import os
import requests
from azure.storage.blob import BlockBlobService, ContentSettings
from operations import (
    read_config,
    CONFIG_PATH,
    get_azure_storage_client
)

class TagData(object):
    def __init__(self, imageUrl, name, tags, x_min, x_max, y_min, y_max, height, width):
        self.tags = tags
        self.x1 = x_min 
        self.x2 = x_max
        self.y1 = y_min
        self.y2 = y_max
        self.height = height
        self.width = width
        self.name = name
        self.imageUrl = imageUrl

def train(config):
    # First, download vott json for tagging complete images
    vott_json = download_vott_json(config)

    # Grab these images from the blob storage
    download_images(vott_json)


def download_images(vott_json):
    blob_storage = get_azure_storage_client(config)
    if not os.path.exists('images'):
        os.makedirs('images')
    for image in vott_json:
        if (blob_storage.exists(config.get("storage_container"), image)):
            blob_storage.get_blob_to_path(config.get("storage_container"),image, "images/{}".format(image))


def download_vott_json(config):
    query = {
        "userName": config.get('tagging_user'),
        "imageCount": 1
    }
    functions_url = config.get('url') + '/api/taggedimages'
    response = requests.get(functions_url, params=query)
    data = response.json()
    print(data)

    vott_json = {}
    index = 0
    for item in data['vottJson']['frames']:
        tags = data['vottJson']['frames'][item]
        array_tags = []
        for tag in tags:
            tagdata = TagData(data['imageUrls'][index], item, tag['tags'], tag['x1'], tag['x2'], tag['y1'], tag['y2'], tag['height'], tag['width'])
            array_tags.append(tagdata)
        vott_json[item] = array_tags
        index += 1
    
    print(vott_json)
    return vott_json
            

if __name__ == "__main__":
    config = read_config(CONFIG_PATH)
    train(config)
