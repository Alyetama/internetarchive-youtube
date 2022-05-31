#!/usr/bin/env python
# coding: utf-8

import os
import sys
from pathlib import Path

import pymongo
import yt_dlp
from dotenv import load_dotenv
from internetarchive import upload
from tqdm import tqdm

from clean_name import clean_fname


def archive_yt_channel(channel_name, db_connection_string, skip_list=None):
    client = pymongo.MongoClient(db_connection_string)
    db = client['yt']
    col = db[channel_name]

    data = list(db[channel_name].find({}))

    for video in tqdm(data):

        _id = video['url'].split('watch?v=')[1]
        if skip_list:
            if _id in skip_list:
                print(f'Skipped {video}...')
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
                ydl.download(video['url'])
            col.update_one({'_id': _id}, {'$set': {'downloaded': True}})

        publish_date = f'{y}-{m}-{d} 00:00:00'

        identifier = f'{y}-{m}-{d}_{channel_name}'
        left_len = 80 - (len(identifier) + 1)
        identifier = f'{identifier}_{clean_name[:left_len]}'

        md = {
            'collection': 'opensource_movies',
            'title': identifier,
            'mediatype': 'movies',
            'description':
            f'Title: {video["title"]}\nPublished on: {publish_date}'
        }

        if not video['uploaded']:
            r = upload(identifier, files=[fname], metadata=md)
            status_code = r[0].status_code
            if status_code == 200:
                col.update_one({'_id': _id}, {'$set': {'uploaded': True}})
                Path(fname).unlink()
            else:
                print(status_code)


if __name__ == '__main__':
    load_dotenv()
    archive_yt_channel(
        channel_name=sys.argv[1],
        db_connection_string=os.getenv('MONGODB_CONNECTION_STRING'))
