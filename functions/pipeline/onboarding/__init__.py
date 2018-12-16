import os
import logging
import json
import azure.functions as func
from urllib.request import urlopen
from PIL import Image
from ..shared.db_provider import get_postgres_provider
from ..shared.db_access import ImageTagDataAccess, ImageInfo
from ..shared.onboarding import copy_images_to_permanent_storage, delete_images_from_temp_storage
from azure.storage.blob import BlockBlobService

DEFAULT_RETURN_HEADER= { "content-type": "application/json" }

COPY_SOURCE = os.getenv('SOURCE_CONTAINER_NAME')
COPY_DESTINATION = os.getenv('DESTINATION_CONTAINER_NAME')
ACCOUNT_NAME=os.getenv('STORAGE_ACCOUNT_NAME')
ACCOUNT_KEY=os.getenv('STORAGE_ACCOUNT_KEY')

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    user_name = req.params.get('userName')

    if not user_name:
        return func.HttpResponse(
            status_code=400,
            headers=DEFAULT_RETURN_HEADER,
            body=json.dumps({"Error": "userName query parameter invalid or omitted."})
        )

    try:
        bodyJson = req.get_json()
        logging.info("Request json: {}".format(bodyJson))
        if "imageUrls" not in bodyJson:
            raise ValueError("invalid request body")
        raw_url_list = bodyJson["imageUrls"]
    except ValueError as ve:
        logging.error("Error: Unable to decode POST body. Error: " + repr(ve))
        return func.HttpResponse(
            status_code=400,
            headers=DEFAULT_RETURN_HEADER,
            body=json.dumps({"Error": "Unable to decode POST body."})
        )

    if not raw_url_list:
        logging.error("Error: URL list empty.")
        return func.HttpResponse(
            status_code=400,
            headers=DEFAULT_RETURN_HEADER,
            body=json.dumps({"Error": "URL list empty."})
        )
    
    # Check to ensure image URLs sent by client are all unique.
    url_list = set(raw_url_list)

    try:
        image_object_list = build_objects_from_url_list(url_list)
    except Exception as e:
        logging.error("Error: Could not build image object list. Exception: " + str(e))
        return func.HttpResponse(
            status_code=400,
            headers=DEFAULT_RETURN_HEADER,
            body=json.dumps({"Error": "Could not build image object list. Exception: " + str(e)})
        )

    try:
        data_access = ImageTagDataAccess(get_postgres_provider())
    except Exception as e:
        logging.error("Error: Database connection failed. Exception: " + str(e))
        return func.HttpResponse(
            status_code=500,
            headers=DEFAULT_RETURN_HEADER,
            body=json.dumps({"Error": "Database connection failed. Exception: " + str(e)})
        )

    # Create/look up username in database and retrieve user_id number
    user_id= data_access.create_user(user_name)
    logging.info("User ID for {0} is {1}".format(user_name, user_id))

    # Add the images to the database and retrieve their image ID's
    logging.info("Add new images to the database, and retrieve a dictionary ImageId's mapped to ImageUrl's")
    image_id_url_map = data_access.add_new_images(image_object_list,user_id)

    # Create blob service for storage account
    blob_service = BlockBlobService(account_name=ACCOUNT_NAME, account_key=ACCOUNT_KEY)

    # Copy images from temporary to permanent storage.  Receive back a list of the copy operations that succeeded and failed.
    # Note: Format for copy_succeeded_dict and copy_error_dict is { sourceURL : destinationURL }
    copy_succeeded_dict, copy_error_dict = copy_images_to_permanent_storage(image_id_url_map, COPY_SOURCE, COPY_DESTINATION, blob_service)

    # Update URLs in DB for images that were successfully copied
    logging.info("Now updating URLs in the DB for images that were successfully copied...")
    # Build new image_id_url_map containing images that were successfully copied
    update_urls_dictionary = {}
    for key in copy_succeeded_dict.keys():
        destination_url = copy_succeeded_dict[key]
        filename = str(destination_url).split('/')[-1]
        image_id_to_update = int(filename.split('.')[0])
        update_urls_dictionary[image_id_to_update] = str(destination_url)
    data_access.update_image_urls(update_urls_dictionary, user_id)
    logging.info("Done.")

    # Delete images from temporary storage.  Receive back a list of the delete operations that succeeded and failed.
    # Note: Format for delete_succeeded_dict and delete_error_dict is { sourceURL : destinationURL }
    logging.info("Now deleting images from temp storage...")
    delete_succeeded_dict, delete_error_dict = delete_images_from_temp_storage(copy_succeeded_dict, COPY_SOURCE, blob_service)
    logging.info("Done.")

    # If both error_dicts are empty, return a 200 OK status code.
    # If copy_error_dict or delete_error_dict contains any items, build a JSON object for HTTP response
    # and return a bad status code indicating that one or more images failed.
    if not copy_error_dict and not delete_error_dict:
        content = json.dumps({"Success": "Transfer of all images complete."})
        return func.HttpResponse(
            status_code=200,
            headers=DEFAULT_RETURN_HEADER,
            body=content
        )
    else:
        content = json.dumps({
            "copy_failed":dict(copy_error_dict),
            "delete_failed":dict(delete_error_dict)
            })
        return func.HttpResponse(
            status_code=500,
            headers=DEFAULT_RETURN_HEADER,
            body=content
        )

# Given a list of image URL's, build an ImageInfo object for each, and return a list of these image objects.
def build_objects_from_url_list(url_list):
    image_object_list = []
    for url in url_list:
        # Split original image name from URL
        original_filename = url.split("/")[-1]
        # Create ImageInfo object (def in db_access.py)
        with Image.open(urlopen(url)) as img:
            width, height = img.size
        image = ImageInfo(original_filename, url, height, width)
        # Append image object to the list
        image_object_list.append(image)
    return image_object_list
