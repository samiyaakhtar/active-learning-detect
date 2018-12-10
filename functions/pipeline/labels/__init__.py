import logging
import jsonpickle
import azure.functions as func
import json
from ..shared.vott_parser import create_starting_vott_json
from ..shared.db_provider import get_postgres_provider
from ..shared.db_access import ImageTagDataAccess, ImageTagState


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

            # TODO: Support POST http calls by merging with the existing "Upload" API.
            # Ideally GET http calls rerurn all human annotated labels. 
            # POST calls save all human annotated labels
            logging.debug("User '{0}' requested labels".format(user_name))

            # Note: Currently we return all human annotated labels since TAGGING.CSV requires all rows
            # No use case to return predicted labels at the moment.
            labels = data_access.get_labels()

            #Encode the complex object nesting
            content = jsonpickle.encode(labels,unpicklable=False)
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