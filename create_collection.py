#!/usr/bin/env python
# coding: utf-8

import argparse
import json
import os
import shlex
import subprocess

import pymongo
from dotenv import load_dotenv
from loguru import logger

from jsonbin_manager import JSONBin


def opts() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('-c',
                        '--channel-url',
                        help='The Channel URL',
                        type=str,
                        required=True)
    parser.add_argument('-n',
                        '--channel-name',
                        help='The channel name',
                        type=str,
                        required=True)
    parser.add_argument('--mongodb', action='store_true', help='Use MongoDB')
    parser.add_argument('--jsonbin', action='store_true', help='Use JSONBIN')
    return parser.parse_args()


def create_collection(channel_url, channel_name, mongodb=True, jsonbin=False):

    cmd = 'yt-dlp --get-filename -o \'{"upload_date": "%(upload_date)s", "title": "%(title)s", "url": "https://www.youtube.com/watch?v=%(id)s", "downloaded": false, "uploaded": false}, \' ' + f'"{channel_url}"'  # noqa

    logger.debug(
        'Downloading the channel\'s metadata... This might take few minutes.')
    p = subprocess.run(shlex.split(cmd),
                       shell=False,
                       check=True,
                       capture_output=True,
                       text=True)
    out = p.stdout
    data = json.loads(f'[{out.strip()[:-1]}]')

    for video in data:
        _id = video['url'].split('watch?v=')[1]
        video.update({'_id': _id})

    data = [dict(x) for x in {tuple(d.items()) for d in data}]

    with open(f'{channel_name}_channel.json', 'w') as j:
        json.dump(data, j, indent=4)

    if mongodb:
        db_connection_string = os.getenv('MONGODB_CONNECTION_STRING')
        client = pymongo.MongoClient(db_connection_string)
        db = client['yt']
        logger.debug(data)
        db[channel_name].insert_many(data)

    elif jsonbin:
        jb = JSONBin(channel_name, os.getenv('JSONBIN_KEY'))
        _ = jb.handle_collection_bins(channel_name, include_data=data)

    return data


if __name__ == '__main__':
    load_dotenv()
    args = opts()

    create_collection(channel_url=args.channel_url,
                      channel_name=args.channel_name,
                      mongodb=args.mongodb,
                      jsonbin=args.jsonbin)
