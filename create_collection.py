#!/usr/bin/env python
# coding: utf-8

import json
import os
import shlex
import subprocess
import sys

import pymongo
from dotenv import load_dotenv


def create_collection(channel_url, channel_name, db_connection_string):

    cmd = 'yt-dlp --get-filename -o \'{"upload_date": "%(upload_date)s", "title": "%(title)s", "url": "https://www.youtube.com/watch?v=%(id)s", "downloaded": false, "uploaded": false}, \' ' + f'"{channel_url}"'  # noqa

    p = subprocess.run(shlex.split(cmd),
                       shell=False,
                       check=True,
                       capture_output=True,
                       text=True)
    out = p.stdout
    data = json.loads(f'[{out.strip()[:-1]}]')

    for x in data:
        _id = x['url'].split('watch?v=')[1]
        x.update({'_id': _id})

    client = pymongo.MongoClient(db_connection_string)
    db = client['yt']
    db[channel_name].insert_many(data)


if __name__ == '__main__':
    load_dotenv()
    create_collection(
        channel_url=sys.argv[1],
        channel_name=sys.argv[2],
        db_connection_string=os.getenv('MONGODB_CONNECTION_STRING'))
