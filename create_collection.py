#!/usr/bin/env python
# coding: utf-8

import json
import os
import shlex
import subprocess

import pymongo
from dotenv import load_dotenv
from loguru import logger

from jsonbin_manager import JSONBin, NoDataToInclude


def mongodb_client(return_names=False):
    client = pymongo.MongoClient(os.getenv('MONGODB_CONNECTION_STRING'))
    db = client['yt']
    if return_names:
        return db.list_collection_names()
    return db


def info_cmd(channel_url, playlist_end=''):
    return f'yt-dlp {playlist_end} --get-filename -o ' \
           '\'{"upload_date": "%(upload_date)s", ' \
           '"title": "%(title)s", "url": ' \
           '"https://www.youtube.com/watch?v=%(id)s", ' \
           '"downloaded": false, "uploaded": false}, \' ' + f'"{channel_url}"'


def create_collection(channel_name, channel_url):
    existing_data = []
    existing_ids = []
    bin_id = None
    skip_full_download = False

    if os.getenv('MONGODB_CONNECTION_STRING'):
        db = mongodb_client()
        existing_data = list(db['DATA'].find({}))
        if existing_data:
            existing_ids = [x.get('_id') for x in existing_data]

    elif os.getenv('JSONBIN_KEY'):
        jb = JSONBin(os.getenv('JSONBIN_KEY'))
        try:
            bin_id = jb.handle_collection_bins()
            existing_data = jb.read_bin(bin_id)
            existing_ids = [x.get('_id') for x in existing_data]
        except NoDataToInclude:
            pass

    cmd_last_ten = info_cmd(channel_url, playlist_end='--playlist-end 10')

    p_last_ten = subprocess.run(shlex.split(cmd_last_ten),
                                shell=False,
                                check=True,
                                capture_output=True,
                                text=True)
    data = json.loads(f'[{p_last_ten.stdout.strip()[:-1]}]')

    for video in data:
        _id = video['url'].split('watch?v=')[1]
        video.update({
            '_id': _id,
            'channel_name': channel_name,
            'channel_url': channel_url
        })

    last_ten_ids = [x['_id'] for x in data]

    if all(True if x in last_ten_ids else False for x in existing_ids):
        print(f'{channel_name} is up-to-date! Nothing to do...')
        return
    else:
        data = [x for x in data if x['_id'] not in existing_ids]
        logger.debug(f'Found {len(data)} new videos...')
        if 10 > len(data):
            skip_full_download = True

    if not skip_full_download:
        logger.debug(
            'Downloading the entire channel metadata... This might take '
            'few minutes...')
        cmd = info_cmd(channel_url)
        p = subprocess.run(shlex.split(cmd),
                           shell=False,
                           check=True,
                           capture_output=True,
                           text=True)
        data = json.loads(f'[{p.stdout.strip()[:-1]}]')

    data = [dict(x) for x in {tuple(d.items()) for d in data}]

    if not data:
        return

    with open(f'{channel_name}_channel.json', 'w') as j:
        json.dump(data, j, indent=4)

    if os.getenv('MONGODB_CONNECTION_STRING'):
        data = [x for x in data if x['_id'] not in existing_ids]
        db['DATA'].insert_many(data)  # noqa

    elif os.getenv('JSONBIN_KEY'):
        if not bin_id:
            bin_id = jb.handle_collection_bins(include_data=data)  # noqa
        data_to_add = []
        for video in data:
            if video['_id'] in existing_ids:
                continue
            else:
                data_to_add.append(video)

        data = existing_data + data_to_add
        jb.update_bin(bin_id, data)

    logger.debug('Finished updating the metadata database...')
    return data


def main():
    channels = os.getenv('CHANNELS')
    channels = [x.split(': ') for x in channels.strip().split('\n')]

    for channel in channels:
        logger.debug(f'Current channel: {channel}')
        _ = create_collection(
            channel_name=channel[0],
            channel_url=channel[1],
        )


if __name__ == '__main__':
    load_dotenv()
    main()
