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
            # Allowing image_count to be empty
            if image_count:
                image_count = int(image_count)

            # Get tag data by status
            image_id_to_urls = data_access.get_images_by_tag_status(user_id, tag_status.split(','), image_count)
            image_id_to_image_tags = data_access.get_image_tags_for_image_ids(list(image_id_to_urls.keys()))

            existing_classifications_list = data_access.get_existing_classifications()

            tags_json = create_starting_vott_json(image_id_to_urls, image_id_to_image_tags, existing_classifications_list)

            content = json.dumps(tags_json)
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
