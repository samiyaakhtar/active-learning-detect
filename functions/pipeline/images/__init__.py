import logging

import azure.functions as func
import json
import jsonpickle
from ..shared.db_provider import get_postgres_provider
from ..shared.db_access import ImageTagDataAccess, ImageTagState


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    image_count = req.params.get('imageCount')
    user_name = req.params.get('userName')
    tag_status = req.params.get('tagStatus')
    image_ids = req.params.get('imageId')
    checkout = req.params.get('checkOut')

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
    elif not tag_status and not image_ids and not checkout:
        return func.HttpResponse(
            status_code=400,
            headers=headers,
            body=json.dumps({"error": "either of tag status or images ids needs to be specified if not checking out images for download"})
        )
    elif checkout and checkout.lower() == "true" and not image_count:
        return func.HttpResponse(
            status_code=400,
            headers=headers,
            body=json.dumps({"error": "image count needs to be specified when checking out images"})
        )
    else:
        try:
            # DB configuration
            data_access = ImageTagDataAccess(get_postgres_provider())
            user_id = data_access.create_user(user_name)

            # This offers download api functionality to check out n images. 
            # We ignore the rest of query params when checkOut is set to true.
            if checkout and checkout.lower() == "true":
                image_count = int(image_count)
                checked_out_images = data_access.checkout_images(image_count, user_id)
                existing_classifications_list = data_access.get_existing_classifications()
                return_body_json = {
                    "images": jsonpickle.encode(checked_out_images, unpicklable=False),
                    "classification_list": existing_classifications_list
                }
                return func.HttpResponse(
                    status_code=200,
                    headers=headers,
                    body=json.dumps(return_body_json)
                )

            # Get images info
            if image_ids:
                image_infos = data_access.get_image_info_for_image_ids(image_ids.split(','))
            elif tag_status:
                if image_count:
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
