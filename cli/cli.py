import argparse

from operations import (
    download,
    upload,
    onboard,
    LOWER_LIMIT,
    UPPER_LIMIT,
    read_config,
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

    config = read_config(CONFIG_PATH)

    if operation == 'download':
        download(config, args.num_images)
    elif operation == 'onboard':
        onboard(config, args.folder)
    else:
        upload(config)
