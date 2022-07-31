#!/usr/bin/env python
# coding: utf-8

import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Optional

import pymongo
from loguru import logger
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from internetarchive_youtube.jsonbin_manager import JSONBin, NoDataToInclude


class InvalidChannelURLFormat(Exception):
    """Raised when the channel URL is not in the correct format."""
    pass


class CreateCollection:

    def __init__(self,
                 channel_name: str,
                 channel_url: str,
                 no_logs: bool = False) -> None:
        """Initialize the class.

        Args:
            channel_name (str): The name of the channel.
            channel_url (str): The URL of the channel.
            no_logs (bool, optional): Whether to disable logging. Defaults to
                False.
        """
        self.channel_name = channel_name
        self.channel_url = channel_url
        self.no_logs = no_logs

    @staticmethod
    def mongodb_client() -> Database:
        """Return a MongoDB client."""
        client = pymongo.MongoClient(os.getenv('MONGODB_CONNECTION_STRING'))
        db = client['yt']
        return db

    def info_cmd(self, playlist_end: str = '') -> Optional[str]:
        """Return the command to get the metadata.

        Args:
            playlist_end (str, optional): The playlist end parameter. Defaults
                to ''.
        """
        # base_url = None
        # if 'youtube' in self.channel_url.lower():
        #     base_url = 'https://www.youtube.com/watch?v='
        # if 'twitch' in self.channel_url.lower():
        #     if '/videos' not in self.channel_url:
        #         raise InvalidChannelURLFormat(
        #             'The format of the channel URL is invalid! Example of a '
        #             'valid URL: https://www.twitch.tv/foobar0228/videos')
        #     base_url = 'https://www.twitch.tv/videos/'

        base_url = 'https://www.youtube.com/watch?v='
        cmd = f'yt-dlp {playlist_end} --get-filename -o ' \
              '\'{"upload_date": "%(upload_date)s", ' \
              '"title": "%(title)s", "url": ' \
              f'"{base_url}%(id)s", ' \
              '"downloaded": false, "uploaded": false}, \' ' + \
              f'"{self.channel_url}"'
        return cmd

    def append_data(self, data: list) -> list:
        """Append the data to the collection.

        Args:
            data (list): The data to append.
        """
        for video in data:
            if 'youtube' in video['url']:
                _id = video['url'].split('watch?v=')[1]
            elif 'twitch' in video['url']:
                _id = Path(video['url']).stem
                if _id.startswith('v'):
                    _id = _id[1:]
                    video['url'] = str(Path(video['url']).parent / _id)
            video.update({
                '_id': _id,  # noqa
                'channel_name': self.channel_name,
                'channel_url': self.channel_url
            })
        return data

    def create_collection(self):
        """Creates the collection."""
        if self.no_logs:
            logger.remove()

        existing_data = []
        existing_ids = []
        bin_id = None
        skip_full_download = False

        if os.getenv('MONGODB_CONNECTION_STRING'):
            db = self.mongodb_client()
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

        cmd_last_ten = self.info_cmd(playlist_end='--playlist-end 10')

        p_last_ten = subprocess.run(shlex.split(cmd_last_ten),
                                    shell=False,
                                    check=True,
                                    capture_output=True,
                                    text=True)
        data = json.loads(f'[{p_last_ten.stdout.strip()[:-1]}]')
        data = self.append_data(data)

        last_ten_ids = [x['_id'] for x in data]

        if all(True if x in last_ten_ids else False for x in existing_ids):
            logger.debug(
                f'{self.channel_name} is up-to-date! Nothing to do...')
            return
        else:
            data = [x for x in data if x['_id'] not in existing_ids]
            if 10 > len(data):
                skip_full_download = True
                logger.debug(f'Found {len(data)} new videos...')

        if not skip_full_download:
            logger.debug(
                'Downloading the entire channel metadata... This might take '
                'few minutes...')
            cmd = self.info_cmd(self.channel_url)
            p = subprocess.run(shlex.split(cmd),
                               shell=False,
                               check=True,
                               capture_output=True,
                               text=True)
            data = json.loads(f'[{p.stdout.strip()[:-1]}]')
            data = self.append_data(data)

        data = [dict(x) for x in {tuple(d.items()) for d in data}]

        if not data:
            return

        with open(f'{self.channel_name}_channel.json', 'w') as j:
            json.dump(data, j, indent=4)

        if os.getenv('MONGODB_CONNECTION_STRING'):
            data = [x for x in data if x['_id'] not in existing_ids]
            for video in data:
                try:
                    db['DATA'].insert_one(video)  # noqa
                except DuplicateKeyError:
                    continue

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
