import logging

import azure.functions as func
import json

from ..shared.vott_parser import create_starting_vott_json
from ..shared.db_provider import get_postgres_provider
from ..shared.db_access import ImageTagDataAccess, ImageTagState


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    image_count = int(req.params.get('imageCount'))
    user_name = req.params.get('userName')
    tag_status = req.params.get('tagStatus')

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
    elif not image_count:
        return func.HttpResponse(
            status_code=400,
            headers=headers,
            body=json.dumps({"error": "image count not specified"})
        )
    elif not tag_status:
        return func.HttpResponse(
            status_code=400,
            headers=headers,
            body=json.dumps({"error": "tag status not specified"})
        )
    else:
        try:
            # DB configuration
            data_access = ImageTagDataAccess(get_postgres_provider())
            user_id = data_access.create_user(user_name)

            # Get images info
            ready_to_tag_images = data_access.get_images_by_tag_status(user_id, tag_status, image_count)

            image_infos = data_access.get_image_info_for_image_ids(list(ready_to_tag_images.keys()))

            # return_body_json = { image_infos }

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
