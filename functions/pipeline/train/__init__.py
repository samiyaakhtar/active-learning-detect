import logging
import jsonpickle
from collections import namedtuple
import azure.functions as func
import json
from ..shared.db_provider import get_postgres_provider
from ..shared.db_access import ImageTagDataAccess, ImageTagState, PredictionLabel, TrainingSession


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

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
    else:
        try:
            # DB configuration
            data_access = ImageTagDataAccess(get_postgres_provider())
            user_id = data_access.create_user(user_name)

            logging.debug("User '{0}' invoked train api".format(user_name))

            logging.info("Method = " + str(req.method))
            if req.method == "GET":
                return func.HttpResponse(
                    status_code=200,
                    headers=headers,
                    body=jsonpickle.encode("Not implemented",unpicklable=False)
                )
            elif req.method == "POST":
                payload = json.loads(req.get_body())
                payload_json = namedtuple('TrainingSession', payload.keys())(*payload.values())
                training_id = data_access.add_training_session(payload_json, user_id)
                return func.HttpResponse(
                    status_code=201,
                    headers=headers,
                    body=str(training_id)
                )
        except Exception as e:
            return func.HttpResponse(
                "exception:" + str(e),
                status_code=500
            )