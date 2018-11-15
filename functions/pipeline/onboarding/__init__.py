import os
import logging
import json
import azure.functions as func

from ..shared.db_provider import get_postgres_provider
from ..shared.db_access import ImageTagDataAccess, ImageInfo
from ..shared.onboarding import copy_images_to_permanent_storage
from azure.storage.blob import BlockBlobService

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    user_name = req.params.get('userName')

    if not user_name:
        return func.HttpResponse(
            status_code=401,
            headers={ "content-type": "application/json"},
            body=json.dumps({"error": "invalid userName given or omitted"})
        )

    try:
        req_body = req.get_json()
        logging.error(req.get_json())
        raw_url_list = req_body["imageUrls"]
    except ValueError:
        logging.error("ERROR: Unable to decode JSON body")
        return func.HttpResponse("ERROR: Unable to decode POST body", status_code=400)

    if not raw_url_list:
        return func.HttpResponse("ERROR: URL list empty.", status_code=401)
    
    # Check to ensure image URLs sent by client are all unique.
    url_list = set(raw_url_list)

    # Get list of image objects to pass to DAL for insertion into DB.
    try:
        image_object_list = build_objects_from_url_list(url_list)
    except Exception as e:
        logging.error("ERROR: Could not build image object list. Exception: " + str(e))
        return func.HttpResponse("ERROR: Could not build image object list.", status_code=401)

    # Connect to database.
    try:
        logging.info("Now connecting to database...")
        data_access = ImageTagDataAccess(get_postgres_provider())
        logging.info("Connected.")
    except Exception as e:
        logging.error("ERROR: Database connection failed.  Exception: " + str(e))
        return func.HttpResponse("ERROR: Unable to connect to database", status_code=503)

    # Create/get user id
    user_id_number = data_access.create_user(user_id)
    logging.info("User id for {0} is {1}".format(user_id, str(user_id_number)))

    # Add new images to the database, and retrieve a dictionary ImageId's mapped to ImageUrl's
    image_id_url_map = data_access.add_new_images(image_object_list,user_id)

    copy_source = os.getenv('SOURCE_CONTAINER_NAME')
    copy_destination = os.getenv('DESTINATION_CONTAINER_NAME')

    # Create blob service for storage account
    blob_service = BlockBlobService(account_name=os.getenv('STORAGE_ACCOUNT_NAME'), account_key=os.getenv('STORAGE_ACCOUNT_KEY'))

    # Copy images to permanent storage and get a dictionary of images for which to update URLs in DB.
    # TODO: Prefer to have this function return a JSON blob as a string containing a list of successes
    # and a list of failures.  If the list of failures contains any items, return a status code other than 200.
    update_urls_dictionary = copy_images_to_permanent_storage(image_id_url_map, copy_source, copy_destination, blob_service)

    # If the dictionary of images is empty, this means a faiure occurred in a copy/delete operation.
    # Otherwise, dictionary contains permanent image URLs for each image ID that was successfully copied.
    if not update_urls_dictionary:
        return func.HttpResponse("ERROR: Image copy/delete operation failed. Check state of images in storage.", status_code=401)
    else:
        logging.info("Now updating permanent URLs in the DB...")
        data_access.update_image_urls(update_urls_dictionary, user_id_number)
        logging.info("Done.")
        # Return string containing list of URLs to images in permanent blob storage
        return func.HttpResponse("Images were successfully added to the database and copied to permanent storage.", status_code=200)

# Given a list ofnimage URL's, build an ImageInfo object for each, and return a list of these image objects.
def build_objects_from_url_list(url_list):
    image_object_list = []
    for url in url_list:
        # Split original image name from URL
        original_filename = url.split("/")[-1]
        # Create ImageInfo object (def in db_access.py)
        # TODO: Figure out where actual height/width need to come from. Values are hard-coded for testing.
        image = ImageInfo(original_filename, url, 50, 50)
        # Append image object to the list
        image_object_list.append(image)
    return image_object_list
  