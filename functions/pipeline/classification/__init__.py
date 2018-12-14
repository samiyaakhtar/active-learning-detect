import logging
import azure.functions as func
import json
from ..shared.db_provider import get_postgres_provider
from ..shared.db_access import ImageTagDataAccess, ImageTagState, PredictionLabel


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    # setup response object
    headers = {
        "content-type": "application/json"
    }
    user_name = req.params.get('userName')
    classes_list = req.params.get("className")
    if not classes_list:
         return func.HttpResponse(
            status_code=401,
            headers=headers,
            body=json.dumps({"error": "invalid classes list given or omitted"})
        )
    elif not user_name:
        return func.HttpResponse(
            status_code=401,
            headers=headers,
            body=json.dumps({"error": "invalid userName given or omitted"})
        )
    try:
        # DB configuration
        data_access = ImageTagDataAccess(get_postgres_provider())
        user_id = data_access.create_user(user_name)

        class_mapping = data_access.get_classification_map(set(classes_list.split(',')), user_id)
        logging.debug("Got classes mapping: " + str(class_mapping))

        return func.HttpResponse(
                        status_code=200,
                        headers=headers,
                        body=json.dumps(class_mapping)
                    )
    except Exception as e:
            return func.HttpResponse(
                "exception:" + str(e),
                status_code=500
            )