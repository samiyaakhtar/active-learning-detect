import logging
import os
from urlpath import URL
from datetime import datetime, timedelta
from azure.storage.blob import BlockBlobService, BlobPermissions

def get_signed_url_for_permstore_blob(permstore_url):
    blob_url = URL(permstore_url)            

    # create sas signature
    blob_service = __get_perm_store_service()
    sas_signature = blob_service.generate_blob_shared_access_signature(
        os.getenv('DESTINATION_CONTAINER_NAME'),
        blob_url.name,
        BlobPermissions.READ,
        datetime.utcnow() + timedelta(hours=1)
    )

    logging.debug("INFO: have sas signature {}".format(sas_signature))
    signed_url = blob_url.with_query(sas_signature)
    return signed_url.as_uri()


def __get_perm_store_service():
    return BlockBlobService(account_name=os.getenv('STORAGE_ACCOUNT_NAME'),
                            account_key=os.getenv('STORAGE_ACCOUNT_KEY'))


def get_filepath_from_url(blob_url: URL, storage_container):
    blob_uri = blob_url.path
    return __remove_postfix(__remove_prefix(blob_uri, '/' + storage_container), '/' + blob_url.name)


def __remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


def __remove_postfix(text, postfix):
    if not text.endswith(postfix):
        return text
    return text[:len(text)-len(postfix)]