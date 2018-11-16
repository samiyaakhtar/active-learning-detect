
import configparser

FUNCTIONS_SECTION = 'FUNCTIONS'
FUNCTIONS_KEY = 'FUNCTIONS_KEY'
FUNCTIONS_URL = 'FUNCTIONS_URL'

STORAGE_SECTION = 'STORAGE'
STORAGE_KEY = 'STORAGE_KEY'
STORAGE_ACCOUNT = 'STORAGE_ACCOUNT'
STORAGE_CONTAINER = 'STORAGE_CONTAINER'

TAGGING_SECTION = 'TAGGING'
TAGGING_LOCATION_KEY = 'TAGGING_LOCATION'
TAGGING_USER_KEY = 'TAGGING_USER'

class Config():
    @staticmethod
    def parse_file(file_name):
        config = {}
        with open(file_name) as file_:
            for line in file_:
                line = line.strip()
                if line and line[0] is not "#":
                    var,value = line.split('=', 1)
                    config[var.strip()] = value.strip()

        return config

    @staticmethod
    def storage_config_section(storage_config_section):
        storage_account_value = storage_config_section.get(STORAGE_ACCOUNT)
        storage_key_value = storage_config_section.get(STORAGE_KEY)
        storage_container_value = storage_config_section.get(STORAGE_CONTAINER)

        if not storage_account_value or not storage_key_value or not storage_container_value:
            raise MissingConfigException()

        return storage_account_value, storage_key_value, storage_container_value

    @staticmethod
    def tagging_config_section(tagging_config_section):
        tagging_location_value = tagging_config_section.get(TAGGING_LOCATION_KEY)
        tagging_user_value = tagging_config_section.get(TAGGING_USER_KEY)

        if not tagging_location_value or not tagging_user_value:
            raise MissingConfigException()

        return tagging_location_value, tagging_user_value
        
    @staticmethod
    def functions_config_section(functions_config_section):
        functions_key_value = functions_config_section.get(FUNCTIONS_KEY)
        functions_url_value = functions_config_section.get(FUNCTIONS_URL)

        if not functions_key_value or not functions_url_value:
            raise MissingConfigException()

        return functions_key_value, functions_url_value
        
    @staticmethod
    def read_config_with_parsed_config(parser):
        sections = parser.sections()

        if FUNCTIONS_SECTION not in sections:
            raise MissingConfigException()

        if STORAGE_SECTION not in sections:
            raise MissingConfigException()

        if TAGGING_SECTION not in sections:
            raise MissingConfigException()

        functions_key, functions_url = Config.functions_config_section(
            parser[FUNCTIONS_SECTION]
        )

        storage_account, storage_key, storage_container = Config.storage_config_section(
            parser[STORAGE_SECTION]
        )

        tagging_location, tagging_user = Config.tagging_config_section(parser[TAGGING_SECTION])

        return {
            "key": functions_key,
            "url": functions_url,
            "storage_account": storage_account,
            "storage_key": storage_key,
            "storage_container": storage_container,
            "tagging_location": tagging_location,
            "tagging_user": tagging_user
        }

    @staticmethod
    def read_config(config_path):
        if config_path is None:
            raise MissingConfigException()

        parser = configparser.ConfigParser()
        parser.read(config_path)
        return Config.read_config_with_parsed_config(parser)

class MissingConfigException(Exception):
    pass