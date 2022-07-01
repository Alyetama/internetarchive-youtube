#!/usr/bin/env python
# coding: utf-8

import os
import random
import re
import string
import time
import uuid
from pathlib import Path
from typing import Optional

import pymongo
import requests
import yt_dlp
from internetarchive import get_item, upload
from loguru import logger
from pymongo.collection import Collection
from tqdm import tqdm

from internetarchive_youtube.jsonbin_manager import JSONBin


class NoStorageSecretFound(Exception):
    """Raised when no storage secret is found in the database"""


class ArchiveYouTube:

    def __init__(self,
                 prioritize: Optional[list] = None,
                 skip_list: Optional[list] = None,
                 force_refresh: bool = True,
                 no_logs: bool = False):
        """Initialize the class.

        Args:
            prioritize: List of channels to prioritize.
            skip_list: List of channels to skip.
            force_refresh: Force refresh of the database.
            no_logs: Disable logging.
        """
        self.prioritize = prioritize
        self.skip_list = skip_list
        self.force_refresh = force_refresh
        self.no_logs = no_logs

    @staticmethod
    def clean_fname(file_name: str) -> str:
        """Clean file name.

        Args:
            file_name (str): File name.

        Returns:
            str: Cleaned file name.
        """

        file_name = Path(file_name)
        illegal = re.sub('[-_]', '', string.punctuation + string.whitespace)
        fname = re.sub(r'\s\[\w+]', '', file_name.stem)
        fname = re.sub(rf'[{illegal}]', '-', fname)
        clean_name = re.sub(r'-+', '_', fname).strip('-') + file_name.suffix
        return clean_name

    def load_data(
        self
    ) -> tuple[bool, bool, Optional[Collection], Optional[JSONBin],
               Optional[str], list]:
        """Load data from the database.

        Returns:
            tuple: (mongodb, jsonbin, col, jb, bin_id, data)
        """

        jsonbin = False
        mongodb = False

        if os.getenv('MONGODB_CONNECTION_STRING'):
            client = pymongo.MongoClient(
                os.getenv('MONGODB_CONNECTION_STRING'))
            db = client['yt']
            col = db['DATA']
            data = list(db['DATA'].find({}))
            mongodb = True
            jb = None
            bin_id = None

        elif os.getenv('JSONBIN_KEY'):
            jb = JSONBin(os.getenv('JSONBIN_KEY'), no_logs=self.no_logs)
            bin_id = jb.handle_collection_bins()
            data = jb.read_bin(bin_id)['record']
            jsonbin = True
            col = None

        else:
            raise NoStorageSecretFound('You need at least one storage secret ('
                                       '`MONGODB_CONNECTION_STRING` or '
                                       '`JSONBIN_KEY`!')

        data = [x for x in data if not x['downloaded'] or not x['uploaded']]

        random.shuffle(data)

        if self.prioritize:
            prioritize = list(map(str.lower, self.prioritize))
            first = []
            second = []
            for item in data:
                if item['channel_name'].lower() in prioritize:
                    first.append(item)
                else:
                    second.append(item)
            data = first + second
        return mongodb, jsonbin, col, jb, bin_id, data

    def create_metadata(self, video: dict) -> tuple[str, str, dict, str]:
        """Create metadata for the video.

        Args:
            video: Video to create metadata for.

        Returns:
            tuple: (id, fname, md, identifier)
        """
        _id = video['_id']
        ts = video['upload_date']
        y, m, d = ts[:4], ts[4:6], ts[6:]
        clean_name = self.clean_fname(video["title"])
        title = f'{y}-{m}-{d}__{clean_name}'
        fname = f'{title}.mp4'

        publish_date = f'{y}-{m}-{d} 00:00:00'

        identifier = f'{y}-{m}-{d}_{video["channel_name"]}'
        left_len = 80 - (len(identifier) + 1)
        identifier = f'{identifier}_{clean_name[:left_len]}'

        custom_fields = {
            k: v
            for k, v in video.items()
            if k not in ['_id', 'downloaded', 'uploaded']
        }
        md = {
            'collection':
            'opensource_movies',
            'mediatype':
            'movies',
            'description':
            f'Title: {video["title"]}\nPublished on: {publish_date}\n'
            f'Original video URL: {video["url"]}',
            'subject':
            video['channel_name'],
            'id':
            _id,
            **custom_fields
        }
        return _id, fname, md, identifier

    @staticmethod
    def download(video: dict, ydl_opts: dict, fname: str) -> Optional[bool]:
        """Download the video.

        Args:
            video: Video to download.
            ydl_opts: Options for youtube-dl.
            fname: Filename to save the video to.

        Returns:
            bool: True if the video was downloaded, False otherwise.
        """
        logger.debug(f'🚀 (CURRENT DOWNLOAD) -> File: {fname}; YT title: '
                     f'{video["title"]}; YT URL: {video["url"]}')

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download(video['url'])
        except yt_dlp.utils.DownloadError as e:
            logger.error(f'❌ Error with video: {video}')
            logger.error(f'❌ ERROR message: {e}')
            logger.debug('Trying again with no format specification...')

            try:
                with yt_dlp.YoutubeDL({'outtmpl': fname}) as ydl:
                    ydl.download(video['url'])
            except yt_dlp.utils.DownloadError as e:
                logger.error(f'❌ Failed again! ERROR message: {e}')
                logger.error(f'❌ Skipping ({video["url"]})...')
                return
        return True

    @staticmethod
    def upload(video: dict, md: dict, identifier: str,
               fname: str) -> Optional[int]:
        """Upload the video.

        Args:
            video: Video to upload.
            md: Metadata for the video.
            identifier: Identifier for the video.
            fname: Filename of the video.

        Returns:
            int: ID of the uploaded video.
        """
        logger.debug(f'Upload metadata: {md}')
        identifier = identifier.replace(' ', '').strip()
        cur_metadata = get_item(identifier).item_metadata
        if cur_metadata.get('metadata'):
            archive_email = os.getenv('ARCHIVE_USER_EMAIL')
            if cur_metadata['metadata']['uploader'] != archive_email:
                identifier = str(uuid.uuid4())
            else:
                logger.debug(f'{video["_id"]} is already uploaded...')
                return

        logger.debug(f'🚀 (CURRENT UPLOAD) -> File: {fname}; Identifier: '
                     f'{identifier}; YT title: {video["title"]}; YT URL: '
                     f'{video["url"]}')

        r = None
        try:
            r = upload(identifier, files=[fname], metadata=md)
        except requests.exceptions.HTTPError as e:
            if 'Slow Down' in str(e) or 'reduce your request rate' in str(e):
                logger.error(f'❌ Error with video: {video}')
                logger.error(f'❌ ERROR message: {e}')
                logger.debug('Sleeping for 60 seconds...')
                time.sleep(60)
                logger.debug('Trying to upload again...')

                try:
                    r = upload(identifier, files=[fname], metadata=md)
                except requests.exceptions.HTTPError as e:
                    logger.error('❌ Failed again!')
                    logger.error(f'❌ ERROR message: {e}')

                    try:
                        identifier = str(uuid.uuid4())
                        r = upload(identifier, files=[fname], metadata=md)
                    except requests.exceptions.HTTPError as e:
                        logger.error(f'❌ ERROR message: {e}')
                        logger.error('❌ Failed all attempts to upload! '
                                     'Skipping...')
                        return

        if r:
            status_code = r[0].status_code
            return status_code

    def run(self) -> None:
        """Run the pipeline."""
        if self.no_logs:
            logger.remove()

        mongodb, jsonbin, col, jb, bin_id, data = self.load_data()

        for video in tqdm(data, desc='Videos'):

            _id, fname, md, identifier = self.create_metadata(video)

            if self.skip_list:
                if _id in self.skip_list:
                    logger.debug(f'Skipped {video} (skip list)...')
                    continue

            ydl_opts = {
                'outtmpl': fname,
                'quiet': True,
                'no-warnings': True,
                'no-progress': True
            }

            if video['downloaded'] and not video['uploaded']:
                if not Path(fname).exists():
                    video['downloaded'] = False

            if not video['downloaded']:
                is_downloaded = self.download(video, ydl_opts, fname)
                if not is_downloaded:
                    continue

                if mongodb:
                    col.update_one({'_id': _id},
                                   {'$set': {
                                       'downloaded': True
                                   }})
                elif jsonbin:
                    video['downloaded'] = True
                    jb.update_bin(bin_id, data)
                logger.debug('✅ Downloaded!')

            if not video['uploaded']:
                status_code = self.upload(video, md, identifier, fname)
                if status_code == 200:
                    if mongodb:
                        col.update_one({'_id': _id},
                                       {'$set': {
                                           'uploaded': True
                                       }})
                    elif jsonbin:
                        video['uploaded'] = True
                        jb.update_bin(bin_id, data)
                    Path(fname).unlink()
                    logger.debug('✅ Uploaded!')
                else:
                    logger.error(f'❌ Could not upload {video}!')
                    logger.error(f'❌ Status code error with video: {video}')

            if self.force_refresh:
                # Update database in current loop for running concurrent jobs
                mongodb, jsonbin, col, jb, bin_id, data = self.load_data()
