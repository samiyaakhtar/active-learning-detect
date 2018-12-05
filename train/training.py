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

def train(config, num_images):

    # First, downloxad data necessary for training
    training_data = download_data_for_training(config, num_images)

    # Make sure directory is clean:
    file_location = Config.initialize_tagging_location(config)

    # Grab tagged and totag images from the blob storage
    download_images(training_data["imageURLs"], str(file_location))

    # create csv file from this data
    convert_to_csv(training_data, str(file_location))


def download_images(imageURLs, file_location):
    print("Downloading images to " + file_location + ", this may take a few seconds...")

    # Download tagged images into tagged folder
    if not os.path.exists(file_location + '/AllImages'):
        os.makedirs(file_location + '/AllImages')
    folder = file_location + '/AllImages'
    for image in imageURLs:
        filename = get_image_name_from_url(image)
        location = image
        # extension = location.split('.')[-1]
        with urllib.request.urlopen(location) as response, open(folder + '/' + str(filename), 'wb') as out_file:
            data = response.read() # a `bytes` object
            out_file.write(data)
    
    print("Downloaded images into " + file_location + "/AllImages/")


def download_data_for_training(config, num_images):
    print("Downloading data for training, this may take a few moments...")
    # Download n images that are ready to tag
    query = {
        "userName": config.get('tagging_user'),
        "imageCount": num_images,
        "tagStatus": 1
    }
    url = config.get('url') + '/api/images'
    response = requests.get(url, params=query)
    to_tag_image_info = response.json()
    image_urls_to_download = [info['location'] for info in to_tag_image_info]

    # Download upto 200 images that have been tagged, for training
    query['tagStatus'] = 3
    query['imageCount'] = 200
    url = config.get('url') + '/api/tags'
    response = requests.get(url, params=query)
    tagged_image_data = response.json()
    image_urls_to_download.extend([tag[0]["location"] for tag in tagged_image_data["frames"].values()])
    return { "imageURLs": image_urls_to_download,
             "toTagImageInfo": to_tag_image_info,
             "taggedImageData": tagged_image_data }


def convert_to_csv(training_data, file_location):
    # Convert tagged images into their own csv
    with open(file_location + '/tagged.csv', 'w') as csvfile:
        filewriter = csv.writer(csvfile, delimiter=',',
                                quotechar='|', quoting=csv.QUOTE_MINIMAL)
        filewriter.writerow(['filename','class','xmin','xmax','ymin','ymax','height','width'])
        for item in training_data["taggedImageData"]["frames"]:
            for tags in training_data["taggedImageData"]["frames"][item]:
                for tag in training_data["taggedImageData"]["frames"][item][0]["tags"]:
                    data = [item, tag, tags['x1'], tags['x2'], tags['y1'], tags['y2'], tags['height'], tags['width']]
                    filewriter.writerow(data)

    # Convert totag images into their own csv
    with open(file_location + '/totag.csv', 'w') as csvfile:
        filewriter = csv.writer(csvfile, delimiter=',',
                                quotechar='|', quoting=csv.QUOTE_MINIMAL)
        filewriter.writerow(['filename','class','xmin','xmax','ymin','ymax','height','width','folder','box_confidence','image_confidence'])
        for item in training_data["toTagImageInfo"]:
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
