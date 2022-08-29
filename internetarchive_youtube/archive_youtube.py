#!/usr/bin/env python
# coding: utf-8

import concurrent.futures
import itertools
import os
import random
import re
import string
import time
import uuid
from pathlib import Path
from typing import Optional, Tuple

import pymongo
import requests
import yt_dlp
from internetarchive import get_item, upload
from loguru import logger
from pymongo.collection import Collection
from tqdm import tqdm

from internetarchive_youtube.jsonbin_manager import JSONBin


class NoStorageSecretFound(Exception):
    """Raised when no storage database secret is found."""


class ArchiveYouTube:

    def __init__(self,
                 prioritize: Optional[list] = None,
                 skip_list: Optional[list] = None,
                 force_refresh: bool = False,
                 no_logs: bool = False,
                 multithreading: bool = False,
                 threads: Optional[int] = None,
                 keep_failed_uploads: bool = False,
                 ignore_video_ids: Optional[list] = None,
                 use_aria2c: bool = False):
        """Initialize the class.

        Args:
            prioritize: List of channels to prioritize.
            skip_list: List of channels to skip.
            force_refresh: Force refresh of the database. Only use when running 
                multiple concurrent CI jobs.
            no_logs: Disable logging.
            multithreading: Use multithreading to process channel videos.
            threads: Maximum threads to use when multithreading is enabled.
        """
        self.prioritize = prioritize
        self.skip_list = skip_list
        self.force_refresh = force_refresh
        self.no_logs = no_logs
        self.multithreading = multithreading
        self.threads = threads
        self.keep_failed_uploads = keep_failed_uploads
        self.ignore_video_ids = ignore_video_ids
        self.use_aria2c = use_aria2c
        self._data = None

    @staticmethod
    def clean_fname(file_name: str) -> str:
        """Clean a file name to remove all special characters.

        Args:
            file_name (str): File name.

        Returns:
            str: Cleaned file name.
        """
        fname = ''.join(
            [x if x in string.printable else '_' for x in file_name])
        fname = re.sub(r'\s\[.+]', '', fname)
        fname = re.sub(r'[^\da-zA-Z]+', '_', fname).strip('_')
        clean_name = re.sub(r'_{2,}', '_', fname)
        return clean_name

    def load_data(
        self
    ) -> Tuple[bool, bool, Optional[Collection], Optional[JSONBin],
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

        if not self.prioritize and os.getenv('PRIORITIZE_CHANNELS'):
            self.prioritize = os.getenv('PRIORITIZE_CHANNELS').split(',')

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

    def create_metadata(self, video: dict) -> Tuple[str, str, dict, str]:
        """Create metadata for the video.

        Args:
            video: Video to create metadata for.

        Returns:
            tuple: (id, title, md, identifier)
        """
        _id = video['_id']
        ts = video['upload_date']
        y, m, d = ts[:4], ts[4:6], ts[6:]
        clean_name = self.clean_fname(video["title"])
        title = f'{y}-{m}-{d}__{clean_name}'

        publish_date = f'{y}-{m}-{d}'
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
            'language':
            'eng',
            'date':
            publish_date,
            **custom_fields
        }
        return _id, title, md, identifier

    @staticmethod
    def download(video: dict, ydl_opts: dict,
                 fname: str) -> Optional[bool]:
        """Download the video.

        Args:
            video: Video to download.
            ydl_opts: Options for youtube-dl.
            fname: Filename to save the video to.

        Returns:
            True if the video was downloaded.
        """
        logger.debug(f'🚀 (CURRENT DOWNLOAD) -> File: {fname}; YT title: '
                     f'{video["title"]}; YT URL: {video["url"]}')

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # info_dict = ydl.extract_info(video['url'], download=False)
                ydl.download(video['url'])
        except yt_dlp.utils.DownloadError as e:
            logger.error(f'❌ Failed to download! ERROR message: {e}')
            logger.error(f'❌ Skipping ({video["url"]})...')

            logger.debug('Removing temporary files...')
            files_here = Path('.').glob('*')
            files_here = [x for x in files_here if fname in x.name]
            tmp_suffixes = ['.ytdl', '.temp', '.part']
            for file in files_here:
                if any(x for x in file.suffixes if x in tmp_suffixes):
                    file.unlink()

            if 'No space left on device' in str(e):
                logger.error(
                    'Running out of local disk space! Terminating the job...')
                raise OSError('No space left on device!')

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
                        return str(e)

        if r:
            status_code = r[0].status_code
            return status_code

    def process_video(self, video: dict, mongodb: bool, jsonbin: bool,
                      col: Optional[Collection], jb: Optional[JSONBin],
                      bin_id: Optional[str]) -> None:
        """Process a video.

        Args:
            video: Video to process.
            mongodb: Whether to save to MongoDB.
            jsonbin: Whether to save to JSONBin.
            col: MongoDB collection to save to.
            jb: JSONBin instance to save to.
            bin_id: JSONBin ID to save to.
        """
        if self.ignore_video_ids:
            if video['_id'] in self.ignore_video_ids:
                logger.debug(
                    f'Video with id {video["_id"]} is on the ignore list. '
                    'Skipping...')
        if self.force_refresh:
            logger.debug('Refreshing the database...')
            mongodb, jsonbin, col, jb, bin_id, self._data = self.load_data()

        _id, base_fname, md, identifier = self.create_metadata(video)

        if self.skip_list:
            if _id in self.skip_list:
                logger.debug(f'Skipped {video} (skip list)...')
                return

        ydl_opts = {'outtmpl': base_fname}

        if self.no_logs:
            ydl_opts.update({
                'quiet': True,
                'no_warnings': True,
                'noprogress': True
            })

        if self.use_aria2c:
            ydl_opts.update({
                'external_downloader': 'aria2c'
                })

        if video['downloaded'] and not video['uploaded']:
            if not Path(base_fname).exists():
                video['downloaded'] = False

        if not video['downloaded']:
            is_downloaded = self.download(video, ydl_opts, base_fname)
            if not is_downloaded:
                return

            if mongodb:
                col.update_one({'_id': _id}, {'$set': {'downloaded': True}})
            elif jsonbin:
                video['downloaded'] = True
                jb.update_bin(bin_id, self._data)
            logger.debug('✅ Downloaded!')
            time.sleep(3)

        if not video['uploaded']:
            suffix = list(Path('.').glob(f'*{base_fname}*'))[0].suffix
            fname = f'{base_fname}{suffix}'
            status_code = self.upload(video, md, identifier, fname)

            if status_code == 200:
                if mongodb:
                    col.update_one({'_id': _id}, {'$set': {'uploaded': True}})
                elif jsonbin:
                    video['uploaded'] = True
                    jb.update_bin(bin_id, self._data)
                logger.debug('✅ Uploaded!')
                Path(fname).unlink()

            else:
                logger.error(f'❌ Could not upload {video}!')
                logger.error(f'❌ Status code {status_code} for video: {video}')
                if not self.keep_failed_uploads:
                    Path(fname).unlink()

    def run(self) -> None:
        """Run the job."""
        if self.no_logs:
            logger.remove()

        mongodb, jsonbin, col, jb, bin_id, data = self.load_data()
        self._data = data
        input_dict = {
            'mongodb': mongodb,
            'jsonbin': jsonbin,
            'col': col,
            'jb': jb,
            'bin_id': bin_id
        }

        if self.multithreading:
            iterators = [
                itertools.repeat(x, len(self._data))
                for x in input_dict.values()
            ]
            max_workers = min(32, os.cpu_count() + 4)
            if self.threads:
                if self.threads > max_workers:
                    self.threads = max_workers
                    logger.warning(
                        'The selected number of threads exceeds the '
                        'recommended number of maximum workers. Falling back '
                        f'to the default value: {max_workers}')

            with concurrent.futures.ThreadPoolExecutor(
                    max_workers=self.threads) as executor:
                _ = list(
                    tqdm(executor.map(self.process_video, self._data,
                                      *iterators),
                         total=len(data),
                         desc='Videos'))

        else:
            for video in tqdm(data, desc='Videos'):
                self.process_video(video=video, **input_dict)
