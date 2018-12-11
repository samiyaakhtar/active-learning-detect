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
from functions.pipeline.shared.db_access import ImageTagState

CONFIG_PATH = os.environ.get('ALCONFIG', None)

def train(config, num_images):

    # First, downloxad data necessary for training
    training_data = download_data_for_training(config, num_images)

    # Make sure directory is clean:
    file_location = Config.initialize_training_location(config)

    # Grab tagged and totag images from the blob storage
    download_images(training_data["imageURLs"], config.get('training_image_dir'))

    # create csv file from this data
    convert_labels_to_csv(training_data["taggedLabelData"],config.get('tagged_output'))


def download_images(imageURLs, file_location): 
    file_location = os.path.expanduser(file_location)
    print("Downloading images to " + file_location + ", this may take a few seconds...")
    # Download tagged images into tagged folder
    if not os.path.exists(file_location):
        os.makedirs(file_location)
    try:
        for image in imageURLs:
            filename = get_image_name_from_url(image)
            location = image
            # extension = location.split('.')[-1]
            with urllib.request.urlopen(location) as response, open(file_location + '/' + str(filename), 'wb') as out_file:
                data = response.read() # a `bytes` object
                out_file.write(data)      
    except Exception as e:
        print("An error occurred attempting to download image at {0}:\n\n{1}".format(image,e))
        raise
    print("Downloaded images into " + file_location)


def download_data_for_training(config, num_images):
    print("Downloading data for training, this may take a few moments...")
    # Download n images that are ready to tag
    query = {
        "userName": config.get('tagging_user'),
        "imageCount": num_images,
        "tagStatus": [  int(ImageTagState.READY_TO_TAG),
                        int(ImageTagState.TAG_IN_PROGRESS),
                        int(ImageTagState.COMPLETED_TAG),
                        int(ImageTagState.INCOMPLETE_TAG)]
    }
    url = config.get('url') + '/api/images'
    response = requests.get(url, params=query)
    all_images_json = response.json()
    image_urls_to_download = [info['location'] for info in all_images_json]

    # Download upto 200 images that have been tagged, for training
    query['tagStatus'] = ImageTagState.COMPLETED_TAG
    query['imageCount'] = 200
    url = config.get('url') + '/api/labels'
    response = requests.get(url, params=query)
    tagged_label_data = response.json()

    return { "imageURLs": image_urls_to_download,
             "taggedLabelData": tagged_label_data }

def convert_labels_to_csv(data, tagging_output_file_path):
    try:
        if not os.path.exists(tagging_output_file_path):
            dir_name = os.path.dirname(tagging_output_file_path)
            if not os.path.exists(dir_name):
                os.makedirs(dir_name)
        with open(tagging_output_file_path, 'w') as csvfile:
            filewriter = csv.writer(csvfile, delimiter=',',quotechar='|', quoting=csv.QUOTE_MINIMAL)
            filewriter.writerow(['filename','class','xmin','xmax','ymin','ymax','height','width'])   
            for img in data:
                imagelocation = get_image_name_from_url(img["imagelocation"])
                image_height = img["image_height"]
                image_width = img["image_width"]
                for label in img["labels"]:
                    data = [imagelocation, label["classificationname"], label['x_min'], label['x_max'], label['y_min'], label['y_max'], image_height, image_width]
                    filewriter.writerow(data)
    except Exception as e:
        print("An error occurred attempting to write to file at {0}:\n\n{1}".format(tagging_output_file_path,e))
        raise

def get_image_name_from_url(image_url):
    start_idx = image_url.rfind('/')+1
    return image_url[start_idx:]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--num-images', type=int)
    config = Config.read_config(CONFIG_PATH)
    args = parser.parse_args()
    train(config, args.num_images)
