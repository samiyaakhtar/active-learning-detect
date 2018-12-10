import json
import logging
from ..shared.db_provider import get_postgres_provider
from ..shared.db_access import ImageTag, ImageTagDataAccess

import azure.functions as func


# Create list of ImageTag objects to write to db for given image_id
def __create_ImageTag_list(image_id, tags_list):
    image_tags = []
    for tag in tags_list:
        image_tags.append(ImageTag(image_id, tag['x1'], tag['x2'], tag['y1'], tag['y2'], tag['classes']))
    return image_tags

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # TODO: Create if check for userId and valid json checks?
        upload_data = req.get_json()
        user_name = req.params.get('userName')

        if not user_name:
            return func.HttpResponse(
                status_code=401,
                headers={ "content-type": "application/json"},
                body=json.dumps({"error": "invalid userName given or omitted"})
            )

        # DB configuration
        data_access = ImageTagDataAccess(get_postgres_provider())
        user_id = data_access.create_user(user_name)

        # Update tagged images
        ids_to_tags = upload_data["imageIdToTags"]

        all_imagetags = []
        for image_id in ids_to_tags.keys():
            if ids_to_tags[image_id]:
                all_imagetags.extend(__create_ImageTag_list(image_id, ids_to_tags[image_id]))

        logging.info("Update all visited images with tags and set state to completed")
        data_access.update_tagged_images(all_imagetags, user_id)

        logging.info("Update visited but no tags identified images")
        data_access.update_completed_untagged_images(upload_data["imagesVisitedNoTag"], user_id)

        logging.info("Update unvisited/incomplete images")
        data_access.update_incomplete_images(upload_data["imagesNotVisited"], user_id)

        return func.HttpResponse(
            body=json.dumps(upload_data),
            status_code=200,
            headers={ "content-type": "application/json"},
        )
    except Exception as e:
        logging.error(str(e))
        return func.HttpResponse(
            "exception:" + str(e),
            status_code=500
        )