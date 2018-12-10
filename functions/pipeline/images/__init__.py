import logging

import azure.functions as func
import json

from ..shared.vott_parser import create_starting_vott_json
from ..shared.db_provider import get_postgres_provider
from ..shared.db_access import ImageTagDataAccess, ImageTagState


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    image_count = req.params.get('imageCount')
    user_name = req.params.get('userName')
    tag_status = req.params.get('tagStatus')
    image_ids = req.params.get('imageId')

    # setup response object
    headers = {
        "content-type": "application/json"
    }
    if not user_name:
        return func.HttpResponse(
            status_code=401,
            headers=headers,
            body=json.dumps({"error": "invalid userName given or omitted"})
        )
    elif not image_count and tag_status:
        return func.HttpResponse(
            status_code=400,
            headers=headers,
            body=json.dumps({"error": "image count needs to be specified if tag status is specified"})
        )
    elif not tag_status and not image_ids:
        return func.HttpResponse(
            status_code=400,
            headers=headers,
            body=json.dumps({"error": "either of tag status or images ids needs to be specified"})
        )
    else:
        try:
            # DB configuration
            data_access = ImageTagDataAccess(get_postgres_provider())
            user_id = data_access.create_user(user_name)

            #TODO: Merge with the existing "Download" API
            # If client adds the querystring param api/images&vott=true 
            # Then we should do "check out" behavior and return a VOTT json in the
            # return payload. This is already implemented in the "Download" API
            # Consequently this "Images" API is all about images and optionally
            # "check out" behavior. This supports both tagging and training needs

            # Get images info
            if image_ids:
                image_infos = data_access.get_image_info_for_image_ids(image_ids.split(','))
            elif tag_status:
                image_count = int(image_count)
                images_by_tag_status = data_access.get_images_by_tag_status(tag_status.split(','), image_count)
                logging.debug("Received {0} images in tag status {1}".format(len(images_by_tag_status),tag_status))
                image_infos = data_access.get_image_info_for_image_ids(list(images_by_tag_status.keys()))

            content = json.dumps(image_infos)
            return func.HttpResponse(
                status_code=200,
                headers=headers,
                body=content
            )
        except Exception as e:
            return func.HttpResponse(
                "exception:" + str(e),
                status_code=500
            )
