#!/usr/bin/env python
# coding: utf-8

import os

import requests
from loguru import logger


class JSONBin:

    def __init__(self,
                 jsonbin_key=os.getenv('JSONBIN_KEY'),
                 bin_id=os.getenv('JSONBIN_ID'),
                 verbose=False):
        self.jsonbin_key = jsonbin_key
        self.bin_id = bin_id
        self.verbose = verbose

    def api_request(self, method=None, data=None):
        headers = {
            'Content-Type': 'application/json',
            'X-Master-Key': os.getenv('JSONBIN_KEY')
        }

        if self.bin_id:
            url = f'https://api.jsonbin.io/v3/b/{self.bin_id}'
        else:
            url = 'https://api.jsonbin.io/v3/b/'
            headers.update({'X-Bin-Name': 'yt_archive_sync'})

        if self.verbose:
            logger.debug(f'Request: {url} {data}')

        if method == 'post':
            resp = requests.post(url, json=data, headers=headers)
        elif method == 'put':
            resp = requests.put(url, json=data, headers=headers)
        else:
            resp = requests.get(url, headers=headers)

        if self.verbose:
            logger.debug(f'Response: {resp.json()}')
        return resp

    def update_bin(self, data):
        read_resp = self.api_request()
        record = read_resp.json()['record']
        for video in record:
            if video['_id'] == data['_id']:
                video.update(data)
                break
        put_resp = self.api_request(method='put', data=record)
        return put_resp.json()
