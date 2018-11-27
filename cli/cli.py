import argparse
import os

from utils.config import Config
from operations import (
    download,
    upload,
    onboard_folder,
    onboard_container,
    LOWER_LIMIT,
    UPPER_LIMIT
)

if __name__ == "__main__":
    # how i want to use the tool:
    # cli.py download --num-images 40
    # cli.py upload
    parser = argparse.ArgumentParser()

    parser.add_argument(
        'operation',
        choices=['download', 'upload', 'onboard']
    )

    parser.add_argument('-f', '--folder')
    parser.add_argument('-c', '--container')
    parser.add_argument('-n', '--num-images', type=int)

    args = parser.parse_args()
    operation = args.operation
    config_path = os.environ.get('ALCONFIG')

    config = Config.read_config(config_path)

    if operation == 'download':
        download(config, args.num_images)
    elif operation == 'onboard':
        if args.folder:
            onboard_folder(config, args.folder)
        elif args.container:
            onboard_container(config, args.container)
        else:
            print("No folder or container argument \
            passed - nothing to onboard")
    else:
        upload(config)
