import logging

import azure.functions as func
import json

from ..shared.vott_parser import create_starting_vott_json
from ..shared.db_provider import get_postgres_provider
from ..shared.db_access import ImageTagDataAccess

MIN_TAGGED_IMAGES_PER_CLASS = 'mintaggedimagesperclass'
MIN_TAGGED_IMAGES = 'mintaggedimages'

def main(req: func.HttpRequest) -> func.HttpResponse:
    config_json = req.get_json()
    logging.info("Config: " + str(config_json))
    
    data_access = ImageTagDataAccess(get_postgres_provider())
    tags_by_class = data_access.get_number_of_tags_by_class()
    logging.info("Tags by class: " + str(tags_by_class))

    rules_satisfied = True
    if MIN_TAGGED_IMAGES_PER_CLASS in config_json:        
        separated = config_json[MIN_TAGGED_IMAGES_PER_CLASS]
        separated = dict(item.lower().split(":") for item in separated.split(","))
        for v, k in tags_by_class:
            if k in separated:
                if v < int(separated[k]):
                    rules_satisfied = False
                    break

    if rules_satisfied and MIN_TAGGED_IMAGES in config_json:
        total_tags = 0
        for v, k in tags_by_class:
            total_tags = total_tags + v
        if total_tags < int(config_json[MIN_TAGGED_IMAGES]):
            rules_satisfied = False

    return func.HttpResponse(
            body=str(rules_satisfied),
            status_code=200,
            headers={ "content-type": "application/json"},
        )