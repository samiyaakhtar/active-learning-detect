import requests
import time
import shutil
import json
import copy
import pathlib
import os
from azure.storage.blob import BlockBlobService, ContentSettings
from utils.blob_utils import BlobStorage
from utils.vott_parser import process_vott_json, create_starting_vott_json, build_id_to_VottImageTag, create_vott_json_from_image_labels
from functions.pipeline.shared.db_access import ImageLabel, ImageTag

DEFAULT_NUM_IMAGES = 40
LOWER_LIMIT = 0
UPPER_LIMIT = 100

azure_storage_client = None

class ImageLimitException(Exception):
    pass


def supported_file_type(file_name):
    file_suffix = pathlib.Path(file_name).suffix.lower()
    if file_suffix in ['.png', '.jpg', '.jpeg', '.gif']:
        return True
    else:
        return False


# TODO We should create the container if it does not exist
def onboard_folder(config, folder_name):
    blob_storage = BlobStorage.get_azure_storage_client(config)
    uri = 'https://' + config.get("storage_account") + '.blob.core.windows.net/' + config.get("storage_container") + '/'
    functions_url = config.get('url') + '/api/onboarding'
    user_name = config.get("tagging_user")
    images = []

    for image in os.listdir(folder_name):
        if not supported_file_type(image):
            continue

        local_path = os.path.join(folder_name, image)
        print('Uploading image ' + image)

        # Upload the created file, use image name for the blob name
        blob_storage.create_blob_from_path(
            config.get("storage_container"),
            image,
            local_path,
            content_settings=ContentSettings(content_type='image/png')
        )

        images.append(uri + image)

    # Post this data to the server to add them to database and kick off active learning
    data = {}
    data['imageUrls'] = images

    query = {
        "code": config.get('key'),
        "userName": user_name
    }

    response = requests.post(functions_url, json=data, params=query)
    response.raise_for_status()

    print("Successfully uploaded images.")
    #TODO: Recent Onboarding refactoring doesn't return ImageURLs anymore
    # json_resp = response.json()
    # count = len(json_resp['imageUrls'])
    # print("Successfully uploaded " + str(count) + " images.")
    # for url in json_resp['imageUrls']:
    #     print(url)


def onboard_container(config, account, key, container):
    print("onboarding from storage container")
    function_url = config.get('url') + '/api/onboardcontainer'
    user_name = config.get("tagging_user")

    print("Onboarding storage container " + container + " into dataset")

    query = {
        "userName": user_name
    }

    data = {
        "storageAccount": account,
        "storageAccountKey": key,
        "storageContainer": container
    }

    resp = requests.post(function_url, params=query, json=data)
    resp.raise_for_status()

    print("Set up container for onboarding. Onboarding may take some time.")


def _download_bounds(num_images):
    images_to_download = num_images

    if num_images is None:
        images_to_download = DEFAULT_NUM_IMAGES

    if images_to_download <= LOWER_LIMIT or images_to_download > UPPER_LIMIT:
        raise ImageLimitException()

    return images_to_download


def download(config, num_images, strategy=None):
    # TODO: better/more proper URI handling.
    functions_url = config.get("url") + "/api/download"
    user_name = config.get("tagging_user")
    images_to_download = _download_bounds(num_images)
    query = {
        "imageCount": images_to_download,
        "userName": user_name
    }

    response = requests.get(functions_url, params=query)
    response.raise_for_status()

    json_resp = response.json()
    images_json = json.loads(json_resp["images"])
    count = len(images_json)

    print("Received " + str(count) + " files.")
    
    if count == 0:
        print("No images could be retrieved with the current retrieval strategy!")
        return

    file_tree = pathlib.Path(os.path.expanduser(
        config.get("tagging_location"))
    )

    if file_tree.exists():
        print("Removing existing tag data directory: " + str(file_tree))

        shutil.rmtree(str(file_tree), ignore_errors=True)

    data_dir = pathlib.Path(file_tree / "data")
    data_dir.mkdir(
        parents=True,
        exist_ok=True
    )
    checkedout_image_labels = [ImageLabel.fromJson(item) for item in images_json]
    vott_json, image_urls = create_vott_json_from_image_labels(checkedout_image_labels, json_resp["classification_list"])

    json_data = {'vott_json': vott_json,
                 'imageUrls': image_urls}

    local_images = download_images(config, data_dir, json_data)
    count = len(local_images)
    print("Successfully downloaded " + str(count) + " images.")
    for image_path in local_images:
        print(image_path)
    print("Ready to tag!")


def download_images(config, image_dir, json_resp):
    print("Downloading files to " + str(image_dir))

    # Write generated VoTT data from the function to a file.
    write_vott_data(image_dir, json_resp)

    urls = json_resp['imageUrls']
    downloaded_file_paths = []
    for index in range(len(urls)):
        url = urls[index]

        file_name = url.split('/')[-1]

        #   TODO: We will download an empty file if we get a permission error on the blob store URL
        # We should raise an exception. For now the blob store must be publically accessible
        response = requests.get(url)
        file_path = pathlib.Path(image_dir / file_name)

        with open(str(file_path), "wb") as file:
            for chunk in response.iter_content(chunk_size=128):
                file.write(chunk)
            file.close()
        downloaded_file_paths.append(file_path)
    return downloaded_file_paths


def write_vott_data(image_dir, json_resp):
    #VOTT expects json file at same level as directory
    data_file = pathlib.Path(image_dir / "../data.json")
    vott_data = json_resp.get("vott_json", None)

    if not vott_data:
        return

    with open(str(data_file), "w") as file:
        vott_json_string = json.dumps(vott_data)
        file.writelines(vott_json_string)
        file.close()


def upload(config):
    functions_url = config.get("url") + "/api/upload"
    user_name = config.get("tagging_user")
    tagging_location = pathlib.Path(
        os.path.expanduser(config.get("tagging_location"))
    )

    print("Uploading VOTT json file...")
    vott_json = pathlib.Path(tagging_location / "data.json")

    with open(str(vott_json)) as json_file:
        json_data = json.load(json_file)
    process_json = process_vott_json(json_data)
    query = {
        "userName": user_name
    }

    response = requests.post(functions_url, json=process_json, params=query)
    response.raise_for_status()

    resp_json = response.json()
    print("Done!")