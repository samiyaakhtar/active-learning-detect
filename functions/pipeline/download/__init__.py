import logging

import azure.functions as func
import json
import jsonpickle
from ..shared.db_provider import get_postgres_provider
from ..shared.db_access import ImageTagDataAccess


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    image_count = req.params.get('imageCount')
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
            image_count = int(image_count)
            data_access = ImageTagDataAccess(get_postgres_provider())
            user_id = data_access.create_user(user_name)
            
            image_count = int(image_count)
            checked_out_images = data_access.checkout_images(image_count, user_id)
            existing_classifications_list = data_access.get_existing_classifications()

            return_body_json = {
                "images": jsonpickle.encode(checked_out_images, unpicklable=False),
                "classification_list": existing_classifications_list
            }

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
