import os
import logging
import json
import azure.functions as func
from urlpath import URL
from datetime import datetime, timedelta
from ..shared.constants import ImageFileType
from ..shared.storage_utils import get_filepath_from_url

from azure.storage.blob import BlockBlobService, BlobPermissions
from azure.storage.queue import QueueService, QueueMessageFormat

DEFAULT_RETURN_HEADER = {
    "content-type": "application/json"
}


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    user_name = req.params.get('userName')

    if not user_name:
        return func.HttpResponse(
            status_code=401,
            headers=DEFAULT_RETURN_HEADER,
            body=json.dumps({"error": "invalid userName given or omitted"})
        )

    try:
        req_body = req.get_json()
        logging.debug(req.get_json())
        storage_account = req_body["storageAccount"]
        storage_account_key = req_body["storageAccountKey"]
        storage_container = req_body["storageContainer"]
    except ValueError:
        return func.HttpResponse(
            "ERROR: Unable to decode POST body",
            status_code=400
        )

    if not storage_container or not storage_account or not storage_account_key:
        return func.HttpResponse(
            "ERROR: storage container/account/key/queue not specified.",
            status_code=401
        )

    # Create blob service for storage account (retrieval source)
    blob_service = BlockBlobService(
        account_name=storage_account,
        account_key=storage_account_key)

    # Queue service for perm storage and queue
    queue_service = QueueService(
        account_name=os.getenv('STORAGE_ACCOUNT_NAME'),
        account_key=os.getenv('STORAGE_ACCOUNT_KEY')
    )

    queue_service.encode_function = QueueMessageFormat.text_base64encode

    try:
        blob_list = []

        for blob_object in blob_service.list_blobs(storage_container):
            blob_url = URL(
                blob_service.make_blob_url(
                    storage_container,
                    blob_object.name
                )
            )
            # Check for supported image types here.
            if ImageFileType.is_supported_filetype(blob_url.suffix):
                logging.debug("INFO: Building sas token for blob " + blob_object.name)
                # create sas signature
                sas_signature = blob_service.generate_blob_shared_access_signature(
                    storage_container,
                    blob_object.name,
                    BlobPermissions.READ,
                    datetime.utcnow() + timedelta(hours=1)
                )

                logging.debug("INFO: have sas signature {}".format(sas_signature))

                signed_url = blob_url.with_query(sas_signature)

                blob_list.append(signed_url.as_uri())

                logging.debug("INFO: Built signed url: {}".format(signed_url))

                msg_body = {
                    "imageUrl": signed_url.as_uri(),
                    "fileName": str(blob_url.name),
                    "fileExtension": str(blob_url.suffix),
                    "directoryComponents": get_filepath_from_url(blob_url, storage_container),
                    "userName": user_name
                }

                body_str = json.dumps(msg_body)
                queue_service.put_message("onboardqueue", body_str)
            else:
                logging.info("Blob object not supported. Object URL={}".format(blob_url.as_uri))

        return func.HttpResponse(
            status_code=202,
            headers=DEFAULT_RETURN_HEADER,
            body=json.dumps(blob_list)
        )
    except Exception as e:
        logging.error("ERROR: Could not build blob object list. Exception: " + str(e))
        return func.HttpResponse("ERROR: Could not get list of blobs in storage_container={0}. Exception={1}".format(
            storage_container, e), status_code=500)
