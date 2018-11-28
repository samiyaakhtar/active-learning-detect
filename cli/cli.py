import argparse
import os

from utils.config import Config
from cli.operations import (
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
    parser.add_argument('-a', '--storage-account')
    parser.add_argument('-c', '--storage-container')
    parser.add_argument('-k', '--storage-key')
    parser.add_argument('-n', '--num-images', type=int)

    args = parser.parse_args()
    operation = args.operation
    config_path = os.environ.get('ALCONFIG')

    config = Config.read_config(config_path)

    if operation == 'download':
        download(config, args.num_images)
    elif operation == 'upload':
        upload(config)
    else:
        if args.folder:
            onboard_folder(config, args.folder)
        elif args.storage_container and args.storage_account and args.storage_key:
            onboard_container(
                config,
                args.storage_account,
                args.storage_key,
                args.storage_container
            )
        else:
            print("No folder, storage account, container, or key argument \
            passed - could not onboard.any")
