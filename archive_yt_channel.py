#!/usr/bin/env python
# coding: utf-8

import os
import uuid
from pathlib import Path

import pymongo
import requests
import yt_dlp
from dotenv import load_dotenv
from internetarchive import upload
from loguru import logger
from tqdm import tqdm

from clean_name import clean_fname
from jsonbin_manager import JSONBin


def archive_yt_channel(skip_list=None):
    jsonbin, mongodb = False, False

    if os.getenv('MONGODB_CONNECTION_STRING'):
        client = pymongo.MongoClient(os.getenv('MONGODB_CONNECTION_STRING'))
        db = client['yt']
        col = db['DATA']
        data = list(db['DATA'].find({}))
        mongodb = True

    elif os.getenv('JSONBIN_KEY'):
        jb = JSONBin(jsonbin_key)
        bin_id = jb.handle_collection_bins()
        data = jb.read_bin(bin_id)['record']
        jsonbin = True

    for video in tqdm(data):

        _id = video['url'].split('watch?v=')[1]
        if skip_list:
            if _id in skip_list:
                logger.debug(f'Skipped {video} (skip list)...')
                continue

        ts = video['upload_date']
        y, m, d = ts[:4], ts[4:6], ts[6:]
        clean_name = clean_fname(video["title"])
        title = f'{y}-{m}-{d}__{clean_name}'
        fname = f'{title}.mp4'

        ydl_opts = {'format': 'mp4/bestaudio+bestvideo', 'outtmpl': fname}

        if video['downloaded'] and not video['uploaded']:
            if not Path(fname).exists():
                video['downloaded'] = False

        if not video['downloaded']:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    ydl.download(video['url'])
                    if mongodb:
                        col.update_one({'_id': _id},
                                       {'$set': {
                                           'downloaded': True
                                       }})
                    elif jsonbin:
                        video['downloaded'] = True
                        jb.update_bin(bin_id, data)
                except yt_dlp.utils.DownloadError as e:
                    logger.error(f'Error with video: {video}')
                    logger.exception(e)
                    continue

        publish_date = f'{y}-{m}-{d} 00:00:00'

        identifier = f'{y}-{m}-{d}_{video["channel_name"]}'
        left_len = 80 - (len(identifier) + 1)
        identifier = f'{identifier}_{clean_name[:left_len]}'

        md = {
            'collection':
            'opensource_movies',
            'title':
            identifier,
            'mediatype':
            'movies',
            'description':
            f'Title: {video["title"]}\nPublished on: {publish_date}\n'
            f'Original video URL: {video["url"]}'
        }

        if not video['uploaded']:
            try:
                r = upload(identifier, files=[fname], metadata=md)
            except requests.exceptions.HTTPError as e:
                try:
                    logger.error(e)
                    r = upload(identifier + str(uuid.uuid4())[:5],
                               files=[fname],
                               metadata=md)
                except requests.exceptions.HTTPError as e:
                    logger.error(f'Error with video: {video}')
                    logger.exception(e)

            status_code = r[0].status_code
            if status_code == 200:
                if mongodb:
                    col.update_one({'_id': _id}, {'$set': {'uploaded': True}})
                elif jsonbin:
                    video['uploaded'] = True
                    jb.update_bin(bin_id, data)
                Path(fname).unlink()
            else:
                logger.error(
                    f'Error uploading {video} (status code: {status_code})')


if __name__ == '__main__':
    load_dotenv()
    archive_yt_channel()
