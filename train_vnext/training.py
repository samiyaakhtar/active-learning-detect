import argparse
import os
import csv
import requests
import datetime
from azure.storage.blob import BlockBlobService, ContentSettings
from utils.blob_utils import BlobStorage
from utils.config import Config
from .validate_config import get_legacy_config, initialize_training_location
import urllib.request
import sys
import time
import jsonpickle
import json
from functions.pipeline.shared.db_access import ImageTagState, PredictionLabel, TrainingSession, Tag

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

    #create label map
    create_pascal_label_map(legacy_config.get('label_map_path'),legacy_config.get('classes').split(","))


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
                    # Create new tag and convert it to relative coordinates
                    tag = Tag(label["classificationname"], float(label['x_min']), float(label['x_max']), float(label['y_min']), float(label['y_max']))
                    # Save it in relative coordinates for training scripts
                    tag.convert_to_relative(int(image_width), int(image_height))
                    data = [imagelocation, 
                            tag.classificationname,                  
                            tag.x_min,
                            tag.x_max, 
                            tag.y_min, 
                            tag.y_max, 
                            image_height, 
                            image_width]
                    filewriter.writerow(data)
        print("Created tagged csv file: " + tagged_output_file_path)
    except Exception as e:
        print("An error occurred attempting to write to file at {0}:\n\n{1}".format(tagged_output_file_path,e))
        raise

def upload_data_post_training(prediction_output_file, classification_name_to_class_id, training_id, user_name,function_url):    
    query = {
        "userName": user_name,
        "trainingId": training_id
    }
    function_url = function_url + "/api/labels"
    payload_json = process_post_training_csv(prediction_output_file, training_id, classification_name_to_class_id)
    requests.post(function_url, params=query, json=payload_json)
    print("Uploaded prediction labels to db.")

def process_post_training_csv(csv_path, training_id, classification_name_to_class_id):
    payload_json = []
    with open(csv_path) as f:
        reader = csv.reader(f)
        next(reader, None) #Skip header
        for row in reader:
            class_name = row[1]
            if class_name in classification_name_to_class_id:
                # Convert the bounding boxes to be with respect to image dimensions
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
                # Save in the database in absolute terms to have parity
                prediction_label.convert_to_absolute()
                payload_json.append(prediction_label)
    return jsonpickle.encode(payload_json, unpicklable=False)

def save_training_session(config, model_location, perf_location, prediction_labels_location):
    # First, upload the model to blob storage
    cur_date_time = "{date:%Y_%m_%d_%H_%M_%S}".format(date=datetime.datetime.utcnow())
    file_name = "frozen_inference_graph_" + cur_date_time + ".pb"
    model_location = upload_model_to_blob_storage(config, model_location, file_name, config.get("tagging_user"))

    # Get the mapping for class name to class id
    overall_average, classification_name_to_class_id, avg_dictionary = process_classifications(perf_location, config.get("tagging_user"), config.get("url"))

    # Create a new training session in db and get its id
    training_id = construct_new_training_session(perf_location, classification_name_to_class_id, overall_average, cur_date_time, model_location, avg_dictionary, config.get("tagging_user"), config.get("url"))

    # Upload prediction labels to the db
    upload_data_post_training(prediction_labels_location, classification_name_to_class_id, training_id, config.get("tagging_user"), config.get("url"))

def upload_model_to_blob_storage(config, model_location, file_name, user_name):
    blob_storage = BlobStorage.get_azure_storage_client(config)
    blob_metadata = {
            "userFilePath": model_location,
            "uploadUser": user_name
        }
    uri = 'https://' + config.get("storage_account") + '.blob.core.windows.net/' + config.get("storage_container") + '/' + file_name
    blob_storage.create_blob_from_path(
            config.get("storage_container"),
            file_name,
            model_location,
            metadata=blob_metadata
        )
    print("Model uploaded at " + str(uri))
    return uri

def construct_new_training_session(perf_location, classification_name_to_class_id, overall_average, training_description, model_location, avg_dictionary, user_name, function_url):
    training_session = TrainingSession(training_description, model_location, overall_average, avg_dictionary)
    query = {
        "userName": user_name
    }
    function_url = function_url + "/api/train"
    payload = jsonpickle.encode(training_session, unpicklable=False)
    response = requests.post(function_url, params=query, json=payload)
    training_id = int(response.json())
    print("Created a new training session with id: " + str(training_id))
    return training_id

def process_classifications(perf_location, user_name,function_url):
    # First build query string to get classification map
    classes = ""
    query = {
        "userName": user_name
    }
    function_url = function_url + "/api/classification"
    overall_average = 0.0
    with open(perf_location) as f:
        content = csv.reader(f, delimiter=',')
        next(content, None) #Skip header
        for line in content:
            class_name = line[0].strip()
            if class_name == "Average":
                overall_average = line[1]
            elif class_name not in classes and class_name != "NULL":
                classes = classes + class_name + ","
    
    query["className"] = classes[:-1]
    print("Getting classification map for classes " + query["className"])
    response = requests.get(function_url, params=query)
    classification_name_to_class_id = response.json()

    # Now that we have classification map, build the dictionary that maps class id : average
    avg_dictionary = {}
    with open(perf_location) as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        next(reader, None) #Skip header
        for row in reader:
            if row[0] != "NULL" and row[0] in classification_name_to_class_id:
                avg_dictionary[classification_name_to_class_id[row[0]]] = row[1]

    return overall_average, classification_name_to_class_id, avg_dictionary

def get_image_name_from_url(image_url):
    start_idx = image_url.rfind('/')+1
    return image_url[start_idx:]

def create_pascal_label_map(label_map_path: str, class_names: list):
    with open(label_map_path, "w") as map_file:
        for index, name in enumerate(class_names, 1):
            map_file.write("item {{\n  id: {}\n  name: '{}'\n}}".format(index, name))
    print("Created Pascal VOC format file: " + label_map_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config-file', required=True)
    parser.add_argument(
        'operation',
        choices=['start', 'save']
    )
    args = parser.parse_args()
    operation = args.operation
    legacy_config = get_legacy_config(args.config_file)
    config = Config.read_config(CONFIG_PATH)

    if operation == "start":
        train(legacy_config, config.get("tagging_user"), config.get("url"))
    elif operation == "save":
        # Upload the model saved at ${inference_output_dir}/frozen_inference_graph.pb
        save_training_session(config, 
                                legacy_config.get("inference_output_dir") + "/frozen_inference_graph.pb",
                                legacy_config.get("validation_output"),
                                legacy_config.get("untagged_output"))