import os
import logging
from enum import Enum
from datetime import datetime
import time
import asyncio

TIMEOUT_SECONDS = 1

class CopyStatus(Enum):
    SUCCESS = "success",
    PENDING = "pending",
    ABORTED = "aborted",
    FAILED = "failed",
    TIMEOUT = "timeout" # custom status

class DeleteStatus(Enum):
    SUCCESS = "success",
    PENDING = "pending",
    ABORTED = "aborted",
    FAILED = "failed",
    TIMEOUT = "timeout" # custom status

# Initiates copy of images from temporary to permanent storage, and checks the status of each operation.
# Returns two dictionaries, copy_succeeded_dict and copy_error_dict, in the format {sourceURL : destinationURL }.
def copy_images_to_permanent_storage(image_id_url_map, copy_source, copy_destination, blob_service):
    copy_initiated_dict = {}        # Dictionary of images for which copy was successfully initiated
    copy_error_dict = {}            # Dictionary of images for which some error/exception occurred

    # Create new blob names
    for key, value in image_id_url_map.items():
        original_blob_url = key
        # original_blob_name = original_blob_url.split("/")[-1]
        file_extension = os.path.splitext(original_blob_url)[1]
        image_id = value
        new_blob_name = (str(image_id) + file_extension)

        # Create the destination blob URL
        destination_blob_path = blob_service.make_blob_url(copy_destination, new_blob_name)

        # Copy blob from temp storage to permanent storage
        logging.info("Now initiating copy of image from temporary to permanent storage...")
        # Log source and destination paths for debugging
        logging.info("Source path: " + original_blob_url)
        logging.info("Destination path: " + destination_blob_path)
        try:
            blob_service.copy_blob(copy_destination, new_blob_name, original_blob_url)
            logging.info("Done.")
            # Add to list of items for which we need to check status if copy was initiated successfully
            copy_initiated_dict[original_blob_url] = destination_blob_path
        except Exception as e:
            logging.error("ERROR: Exception thrown during copy attempt: " + str(e))
            copy_error_dict[original_blob_url] = destination_blob_path

    # Wait a few seconds before checking status
    time.sleep(TIMEOUT_SECONDS)

    copy_succeeded_dict = {}        # Dictionary of copy operations that were successful

    # Get copy status of each item.  If status is succeeded, add to success list.  Otherwise, add to error list.
    for key, value in copy_initiated_dict.items():
        target_blob_properties = blob_service.get_blob_properties(copy_destination, value.split("/")[-1])
        copy_properties = target_blob_properties.properties.copy
        # logging.info("Copy status of image" + value.split("/")[-1] + " is: " + copy_properties.status)     # Debugging
        # if copy_properties.status == CopyStatus.SUCCESS:    # Note: Want to remove hard-coding, but this line does not work
        if copy_properties.status == "success":
            copy_succeeded_dict[key] = value
        else:
            copy_error_dict[key] = value
    
    # Debugging
    # logging.info("copy_succeeded_dict:")
    # for key, value in copy_succeeded_dict.items():
    #     logging.info("Key: " + key + " Value: " + value)
    # logging.info("copy_error_dict:")
    # for key, value in copy_error_dict.items():
    #     logging.info("Key: " + key + " Value: " + value)
    
    return copy_succeeded_dict, copy_error_dict

# Initiates deletion of images from temporary storage, and then checks whether the images still exist in the container.
# Returns two dictionaries, delete_succeeded_dict and delete_error_dict, in the format {sourceURL : destinationURL }.
def delete_images_from_temp_storage(delete_images_dict, delete_location, blob_service):
    delete_initiated_dict = {}        # Dictionary of images for which delete was successfully initiated
    delete_error_dict = {}            # Dictionary of images for which some error/exception occurred

    # Delete blobs from container
    for key, value in delete_images_dict.items():
        logging.info("Now initiating delete of image from temp storage...")
        logging.info("Image to be deleted: " + key)
        try:
            blob_service.delete_blob(delete_location, key.split("/")[-1])
            logging.info("Done.")
            # Add to list of items to check status if delete was initiated successfully
            delete_initiated_dict[key] = value
        except Exception as e:
            logging.error("ERROR: Exception thrown during delete attempt: " + str(e))
            delete_error_dict[key] = value

    # Wait a few seconds before checking status
    time.sleep(TIMEOUT_SECONDS)

    delete_succeeded_dict = {}        # Dictionary of delete operations that were successful

    # List blobs in the source container.  For each image in delete_initiated_dict, if the blob no longer exists,
    # add to delete_succeeded_dict.  If the blob still exists, add to delete_error_dict.
    blob_list = blob_service.list_blobs(delete_location)
    for key, value in delete_initiated_dict.items():
        blob_name = key.split('/')[-1]
        if blob_name in blob_list:
            delete_error_dict[key] = value
        else:
            delete_succeeded_dict[key] = value
    
    return delete_succeeded_dict, delete_error_dict