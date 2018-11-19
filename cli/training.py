import argparse
import os
import requests
from azure.storage.blob import BlockBlobService, ContentSettings
from utils.config import Config
from utils.blob_utils import BlobStorage

CONFIG_PATH = os.environ.get('ALCONFIG', None)

class TagData(object):
    def __init__(self, imageUrl, name, tags, x1, x2, y1, y2, height, width):
        self.tags = tags
        self.x1 = x1 
        self.x2 = x2
        self.y1 = y1
        self.y2 = y2
        self.height = height
        self.width = width
        self.name = name
        self.imageUrl = imageUrl

def train(config, num_images):
    # First, download vott json for tagging complete images
    vott_json = download_vott_json(config, num_images)

    # Grab these images from the blob storage
    download_images(vott_json)


def download_images(vott_json):
    blob_storage = BlobStorage.get_azure_storage_client(config)
    if not os.path.exists('images'):
        os.makedirs('images')
    for image in vott_json:
        if (blob_storage.exists(config.get("storage_container"), image)):
            blob_storage.get_blob_to_path(config.get("storage_container"),image, "images/{}".format(image))


def download_vott_json(config, num_images):
    query = {
        "userName": config.get('tagging_user'),
        "imageCount": num_images
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
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--num-images', type=int)
    config = Config.read_config(CONFIG_PATH)
    args = parser.parse_args()
    train(config, args.num_images)
