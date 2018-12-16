import argparse
import os
import csv
import requests
from azure.storage.blob import BlockBlobService, ContentSettings
from utils.blob_utils import BlobStorage
from utils.config import Config
from .validate_config import get_legacy_config, initialize_training_location
import urllib.request
import sys
import time
import jsonpickle
from functions.pipeline.shared.db_access import ImageTagState, PredictionLabel

CONFIG_PATH = os.environ.get('ALCONFIG', None)

def train(legacy_config, user_name, function_url):

    # First, downloxad data necessary for training
    training_data = download_data_for_training(user_name, function_url)

    # Make sure directory is clean:
    file_location = initialize_training_location(legacy_config)

    # Grab tagged and totag images from the blob storage
    download_images(training_data["imageURLs"], legacy_config.get('image_dir'))

    # create csv file from this data
    convert_tagged_labels_to_csv(training_data["taggedLabelData"],legacy_config.get('tagged_output'))
    convert_tagging_labels_to_csv(training_data["taggingLabelData"], legacy_config.get('tagging_output'))


def download_images(image_urls, folder_location): 
    folder_location = os.path.expanduser(folder_location)
    print("Syncing images to " + folder_location)

    if not os.path.exists(folder_location):
        print("Directory doesn't exist so downloading all images may take a few minutes...")
        os.makedirs(folder_location)

    existing_files = {os.path.relpath(os.path.join(directory, cur_file), folder_location) for (directory, _, filenames) 
        in os.walk(folder_location) for cur_file in filenames}

    try:
        for image_url in image_urls:
            file_name = get_image_name_from_url(image_url)
            if file_name not in existing_files:
                with urllib.request.urlopen(image_url) as response, open(folder_location + '/' + str(file_name), 'wb') as out_file:
                    data = response.read() # a `bytes` object
                    out_file.write(data)      
    except Exception as e:
        print("An error occurred attempting to download image at {0}:\n\n{1}".format(image_url,e))
        raise
    print("Synced images into " + folder_location)


def download_data_for_training(user_name, function_url):
    print("Downloading data for training, this may take a few moments...")
    # Download all images to begin training
    query = {
        "userName": user_name,
        "tagStatus": [  int(ImageTagState.READY_TO_TAG),
                        int(ImageTagState.TAG_IN_PROGRESS),
                        int(ImageTagState.COMPLETED_TAG),
                        int(ImageTagState.INCOMPLETE_TAG)]
    }
    url = function_url + '/api/images'
    response = requests.get(url, params=query)
    all_images_json = response.json()
    image_urls_to_download = [info['location'] for info in all_images_json]

    # Download upto 200 images that have been tagged, for training
    query['tagStatus'] = ImageTagState.COMPLETED_TAG
    query['imageCount'] = 200
    url = function_url + '/api/labels'
    response = requests.get(url, params=query)
    tagged_label_data = response.json()

    tagging_image_data = set([get_image_name_from_url(item['location']) for item in all_images_json if item['tagstate'] == ImageTagState.TAG_IN_PROGRESS])
    return { "imageURLs": image_urls_to_download,
             "taggedLabelData": tagged_label_data,
             "taggingLabelData": tagging_image_data }

def convert_tagging_labels_to_csv(filenames, tagging_output_file_path):
    try:
        if not os.path.exists(tagging_output_file_path):
            dir_name = os.path.dirname(tagging_output_file_path)
            if not os.path.exists(dir_name):
                os.makedirs(dir_name)
        with open(tagging_output_file_path, 'w') as csvfile:
            for img in filenames:
                csvfile.write(img + '\n')
        print("Created tagging csv file: " + tagging_output_file_path)
    except Exception as e:
        print("An error occurred attempting to write to file at {0}:\n\n{1}".format(tagging_output_file_path,e))
        raise

def convert_tagged_labels_to_csv(data, tagged_output_file_path):
    try:
        if not os.path.exists(tagged_output_file_path):
            dir_name = os.path.dirname(tagged_output_file_path)
            if not os.path.exists(dir_name):
                os.makedirs(dir_name)
        with open(tagged_output_file_path, 'w') as csvfile:
            filewriter = csv.writer(csvfile, delimiter=',',quotechar='|', quoting=csv.QUOTE_MINIMAL)
            filewriter.writerow(['filename','class','xmin','xmax','ymin','ymax','height','width'])   
            for img in data:
                imagelocation = get_image_name_from_url(img["imagelocation"])
                image_height = img["image_height"]
                image_width = img["image_width"]
                for label in img["labels"]:
                    data = [imagelocation, label["classificationname"], label['x_min'], label['x_max'], label['y_min'], label['y_max'], image_height, image_width]
                    filewriter.writerow(data)
        print("Created tagged csv file: " + tagged_output_file_path)
    except Exception as e:
        print("An error occurred attempting to write to file at {0}:\n\n{1}".format(tagged_output_file_path,e))
        raise

def upload_data_post_training(prediction_output_file, training_id, user_name,function_url):
    function_url = function_url + "/api/classification"
    query = {
        "userName": user_name
    }

    # First, we need to get a mapping of class names to class ids
    classes = ""
    with open(prediction_output_file) as f:
        content = f.readlines()
        for line in content:
            class_name = line.strip().split(',')[1]
            if class_name not in classes:
                classes = classes + class_name + ","
    
    query["className"] = classes[:-1]
    response = requests.get(function_url, params=query)
    classification_name_to_class_id = response.json()
    
    # Now that we have a mapping, we create prediction labels in db
    query = {
        "userName": user_name,
        "trainingId": training_id
    }
    function_url = function_url + "/api/labels"
    payload_json = process_post_training_csv(prediction_output_file, training_id, classification_name_to_class_id)
    requests.post(function_url, params=query, json=payload_json)

def process_post_training_csv(csv_path, training_id, classification_name_to_class_id):
    payload_json = []
    with open(csv_path) as f:
        reader = csv.reader(f)
        next(reader, None) #Skip header
        for row in reader:
            class_name = row[1]
            if class_name in classification_name_to_class_id:
                prediction_label = PredictionLabel(training_id, 
                                    int(row[0].split('.')[0]), 
                                    classification_name_to_class_id[class_name], 
                                    float(row[2]), 
                                    float(row[3]), 
                                    float(row[4]), 
                                    float(row[5]), 
                                    int(row[6]), 
                                    int(row[7]), 
                                    float(row[8]), 
                                    float(row[9]))
                payload_json.append(prediction_label)
    return jsonpickle.encode(payload_json, unpicklable=False)

def get_image_name_from_url(image_url):
    start_idx = image_url.rfind('/')+1
    return image_url[start_idx:]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config-file', required=True)
    args = parser.parse_args()
    legacy_config = get_legacy_config(args.config_file)
    config = Config.read_config(CONFIG_PATH)
    train(legacy_config, config.get("tagging_user"), config.get("url"))