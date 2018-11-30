import argparse
# from utils.config import Config
import configparser
import requests
import json

def parse_config(config_file):
    config = configparser.ConfigParser()
    config.read(config_file)
    response = requests.get(config['FUNCTIONS']['FUNCTIONS_URL'] + '/api/train', json=config._sections['RULES'])
    print(response.text)
    response.raise_for_status()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config')
    args = parser.parse_args()
    parse_config(args.config)
