#!/usr/bin/env python
# coding: utf-8

import json
import os
import shlex
import subprocess

import pymongo
from dotenv import load_dotenv
from loguru import logger

from jsonbin_manager import JSONBin


def mongodb_client(return_names=False):
    client = pymongo.MongoClient(os.getenv('MONGODB_CONNECTION_STRING'))
    db = client['yt']
    if return_names:
        return db.list_collection_names()
    return db


def create_collection(channel_name, channel_url):

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
        video.update({
            '_id': _id,
            'channel_name': channel_name,
            'channel_url': channel_url
        })

    data = [dict(x) for x in {tuple(d.items()) for d in data}]

    with open(f'{channel_name}_channel.json', 'w') as j:
        json.dump(data, j, indent=4)

    if os.getenv('MONGODB_CONNECTION_STRING'):
        db = mongodb_client()
        logger.debug(data)
        existing_data = list(db['DATA'].find({'_id': 1}))
        for video in data:
            try:
                db['DATA'].insert_one(video)
            except pymongo.errors.DuplicateKeyError:
                continue

    elif os.getenv('JSONBIN_KEY'):
        jb = JSONBin(os.getenv('JSONBIN_KEY'))
        bin_id = jb.handle_collection_bins(include_data=data)
        existing_data = jb.read_bin(bin_id)
        existing_ids = [x['_id'] for x in existing_data]
        data_to_add = []

        for video in data:
            if video['_id'] in existing_ids:
                continue
            else:
                data_to_add.append(video)

        data = existing_data + data_to_add
        jb.update_bin(bin_id, data)

    return data


def main():
    channels = os.getenv('CHANNELS')
    channels = [x.split(': ') for x in channels.strip().split('\n')]

    for channel in channels:
        print(f'Current channel: {channel}')
        _ = create_collection(
            channel_name=channel[0],
            channel_url=channel[1],
        )


if __name__ == '__main__':
    load_dotenv()
    main()
