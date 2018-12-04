import argparse
import os
import csv
import requests
from azure.storage.blob import BlockBlobService, ContentSettings
from utils.config import Config
from utils.blob_utils import BlobStorage
import urllib.request

import sys
import time

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
    # First, downloxad vott json for tagging complete images
    vott_json = download_vott_json(config, num_images)

    # Make sure directory is clean:
    file_location = Config.initialize_tagging_location(config)

    # Grab tagged and totag images from the blob storage
    download_images(vott_json, str(file_location))

    # create csv file from this data
    convert_to_csv(vott_json, str(file_location))


def download_images(vott_json, file_location):
    blob_storage = BlobStorage.get_azure_storage_client(config)
    print("Downloading images to " + file_location + ", this may take a few seconds...")

    # Download tagged images into tagged folder
    if not os.path.exists(file_location + '/tagged'):
        os.makedirs(file_location + '/tagged')
    folder = file_location + '/tagged'
    for image in vott_json["taggedImages"]:
        if (blob_storage.exists(config.get("storage_container"), image)):
            blob_storage.get_blob_to_path(config.get("storage_container"),image, "{0}/{1}".format(folder, image))

    # Download totag images into totag folder
    if not os.path.exists(file_location + '/totag'):
        os.makedirs(file_location + '/totag')
    folder = file_location + '/totag'
    for image in vott_json["toTagImageInfo"]:
        filename = image['id']
        extension = image['location'].split('.')[-1]
        with urllib.request.urlopen(image['location']) as response, open(folder + '/' + str(filename) + '.' + extension, 'wb') as out_file:
            data = response.read() # a `bytes` object
            out_file.write(data)
    
    print("Downloaded images into " + file_location + "/tagged/ and " + file_location + "/totag/")


def download_vott_json(config, num_images):
    query = {
        "userName": config.get('tagging_user'),
        "imageCount": num_images
    }
    functions_url = config.get('url') + '/api/taggedimages'
    print("Downloading data for training, this may take a few minutes...")
    response = requests.get(functions_url, params=query)
    data = response.json()

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
    return {
        "taggedImages": vott_json,
        "toTagImageInfo": data["toTagImageInfo"]
    }


def convert_to_csv(vott_json, file_location):
    # Convert tagged images into their own csv
    with open(file_location + '/tagged.csv', 'w') as csvfile:
        filewriter = csv.writer(csvfile, delimiter=',',
                                quotechar='|', quoting=csv.QUOTE_MINIMAL)
        filewriter.writerow(['filename','class','xmin','xmax','ymin','ymax','height','width'])
        for item in vott_json["taggedImages"]:
            for tags in vott_json["taggedImages"][item]:
                for tag in tags.tags:
                    data = [tags.name, tag, tags.x1, tags.x2, tags.y1, tags.y2, tags.height, tags.width]
                    filewriter.writerow(data)

    # Convert totag images into their own csv
    with open(file_location + '/totag.csv', 'w') as csvfile:
        filewriter = csv.writer(csvfile, delimiter=',',
                                quotechar='|', quoting=csv.QUOTE_MINIMAL)
        filewriter.writerow(['filename','class','xmin','xmax','ymin','ymax','height','width','folder','box_confidence','image_confidence'])
        for item in vott_json["toTagImageInfo"]:
            filename = get_image_name_from_url(item['location'])
            data = [filename, 'NULL', 0, 0, 0, 0, item['height'], item['width'], '', 0, 0]
            filewriter.writerow(data)
    
    print("Created csv files with metadata " + file_location + "/tagged.csv and " + file_location + "/totag.csv")


def get_image_name_from_url(image_url):
    s = image_url.split('/')
    return s[len(s)-1]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--num-images', type=int)
    config = Config.read_config(CONFIG_PATH)
    args = parser.parse_args()
    train(config, args.num_images)
