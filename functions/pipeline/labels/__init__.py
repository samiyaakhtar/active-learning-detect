import logging
import jsonpickle
from collections import namedtuple
import azure.functions as func
import json
from ..shared.db_provider import get_postgres_provider
from ..shared.db_access import ImageTagDataAccess, ImageTagState, PredictionLabel, ImageTag

DEFAULT_RETURN_HEADER= { "content-type": "application/json" }

# GET returns all human annotated labels
# POST calls with upload=true flag save all human annotated labels
# POST calls with trainingId param save predicted labels 
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    user_name = req.params.get('userName')
    training_id = req.params.get("trainingId")
    upload = req.params.get("upload")
    
    if not user_name:
        return func.HttpResponse(
            status_code=401,
            headers=DEFAULT_RETURN_HEADER,
            body=json.dumps({"error": "invalid userName given or omitted"})
        )
    elif req.method == "POST" and not upload and not training_id:
        return func.HttpResponse(
            status_code=401,
            headers=DEFAULT_RETURN_HEADER,
            body=json.dumps({"error": "trainingId or upload flag needs to be specified with a POST request"})
        )
    else:
        try:
            # DB configuration
            data_access = ImageTagDataAccess(get_postgres_provider())
            user_id = data_access.create_user(user_name)

            logging.debug("User '{0}' invoked labels api".format(user_name))

            if req.method == "GET":
                # Note: Currently we return all human annotated labels since TAGGING.CSV requires all rows
                # No use case to return predicted labels at the moment.
                labels = data_access.get_labels()

                #Encode the complex object nesting
                content = jsonpickle.encode(labels,unpicklable=False)
                return func.HttpResponse(
                    status_code=200,
                    headers=DEFAULT_RETURN_HEADER,
                    body=content
                )
            elif req.method == "POST" and upload and upload.lower() == "true":
                try:
                    upload_data = req.get_json()
                except ValueError as ve:
                    logging.error("Error: Unable to decode POST body. Error: " + repr(ve))
                    return func.HttpResponse(
                        status_code=401,
                        headers=DEFAULT_RETURN_HEADER,
                        body=json.dumps({"Error": "Unable to decode POST body."})
                    )
                __upload_tag_data(upload_data, data_access, user_id)

                return func.HttpResponse(
                    body=json.dumps(upload_data),
                    status_code=201,
                    headers=DEFAULT_RETURN_HEADER,
                )
            elif req.method == "POST" and training_id:
                payload = json.loads(req.get_body())
                if not training_id:
                    return func.HttpResponse(
                        status_code=401,
                        headers=DEFAULT_RETURN_HEADER,
                        body=json.dumps({"error": "invalid training_id given or omitted"})
                    )
                training_id = int(training_id)
                payload_json = [namedtuple('PredictionLabel', item.keys())(*item.values()) for item in payload]
                data_access.add_prediction_labels(payload_json, training_id)
                return func.HttpResponse(
                    status_code=201,
                    headers=DEFAULT_RETURN_HEADER
                )

        except Exception as e:
            return func.HttpResponse(
                "exception:" + str(e),
                status_code=500
            )

def __upload_tag_data(upload_data, data_access, user_id):
    ids_to_tags = upload_data["imageIdToTags"]

    all_imagetags = []
    for image_id in ids_to_tags.keys():
        if ids_to_tags[image_id]:
            all_imagetags.extend(__create_ImageTag_list(image_id, ids_to_tags[image_id]))

    unique_class_names = upload_data["uniqueClassNames"]
    if all_imagetags and unique_class_names:
        logging.info("Update all visited images with tags and set state to completed")        
        class_map = data_access.get_classification_map(unique_class_names,user_id)
        annotated_labels = data_access.convert_to_annotated_label(all_imagetags,class_map)
        data_access.update_tagged_images_v2(annotated_labels,user_id)
    else:
        logging.info("No tagged image ids or classifications received")

    logging.info("Update visited but no tags identified images")
    data_access.update_completed_untagged_images(upload_data["imagesVisitedNoTag"], user_id)

    logging.info("Update unvisited/incomplete images")
    data_access.update_incomplete_images(upload_data["imagesNotVisited"], user_id)

# Create list of ImageTag objects to write to db for given image_id
def __create_ImageTag_list(image_id, tags_list):
    image_tags = []
    for tag in tags_list:
        image_tags.append(ImageTag(image_id, tag['x1'], tag['x2'], tag['y1'], tag['y2'], tag['classes']))
    return image_tags