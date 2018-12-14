import os
import sys
from pathlib import Path
path = os.path.join(os.path.dirname(__file__), os.pardir)
sys.path.append(path)
from utils.config import Config

class IllegalArgumentError(ValueError):
    pass

def validate_value(config: dict, key_name: str):
    return_val = config[key_name]
    if not return_val:
        raise IllegalArgumentError("Need value for {} in legacy config file".format(key_name))
    return return_val

def get_legacy_config(config_path: str) -> dict:
    legacy_config_file = {}
    try:            
        legacy_config_file = Config.parse_file(config_path)
    except Exception as e:
        print("An error occurred attempting to read to file at {0}:\n\n{1}".format(config_path,e))
        raise

    result = {}
    keys_we_care_about = ["data_dir","tagged_output","image_dir","filetype","classes"]

    for key_name in keys_we_care_about:
        os.environ[key_name] = validate_value(legacy_config_file,key_name)   
        result[key_name] = os.path.expandvars(os.environ[key_name])

    if legacy_config_file["user_folders"] == True:
        raise IllegalArgumentError("Currently we do not support user folders. Change setting in {}".format(config_path))
    #TODO: Validate that the images we have match the filetype
    #TODO: Make sure the classifications exist in the DB
    return result

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file-path', type=str)
    args = parser.parse_args()
    print(get_legacy_config(args.file_path))

