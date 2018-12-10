import logging

import azure.functions as func
import json

from ..shared.db_provider import get_postgres_provider
from ..shared.db_access import ImageTagDataAccess


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    image_count = int(req.params.get('imageCount'))
    user_name = req.params.get('userName')

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
    else:
        try:
            # DB configuration
            data_access = ImageTagDataAccess(get_postgres_provider())
            user_id = data_access.create_user(user_name)
            image_id_to_urls = data_access.get_images_for_tagging(image_count, user_id)
            image_urls = list(image_id_to_urls.values())

            image_id_to_image_tags = {}
            for image_id in image_id_to_urls.keys():
                image_id_to_image_tags[image_id] = data_access.get_image_tags(image_id)

            existing_classifications_list = data_access.get_existing_classifications()

            return_body_json = {"imageUrls": image_urls,
                                "image_id_to_urls": image_id_to_urls,
                                "image_id_to_image_tags": image_id_to_image_tags,
                                "existing_classifications_list": existing_classifications_list}

            content = json.dumps(return_body_json)
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
