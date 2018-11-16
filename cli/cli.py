import argparse
import sys
from pathlib import Path

sys.path.append("../utils")
from config import Config
from blob_utils import BlobStorage

from operations import (
    download,
    upload,
    onboard,
    LOWER_LIMIT,
    UPPER_LIMIT,
    CONFIG_PATH
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
    parser.add_argument('-n', '--num-images', type=int)
    args = parser.parse_args()

    operation = args.operation

    config = Config.read_config(CONFIG_PATH)

    if operation == 'download':
        download(config, args.num_images)
    elif operation == 'onboard':
        onboard(config, args.folder)
    else:
        upload(config)

