#!/usr/bin/env python
# coding: utf-8

import requests


class JSONBin:

    def __init__(self, jsonbin_key):
        self.jsonbin_key = jsonbin_key

    def handle_collection_bins(self, include_data=None):
        url = 'https://api.jsonbin.io/v3'

        headers = {
            'X-Collection-Name': 'yt_archive_sync_collection',
            'X-Master-Key': self.jsonbin_key
        }
        data = {}

        # CREATE A COLLECTION

        resp = requests.post(f'{url}/c', json=data, headers=headers).json()
        if resp.get('record'):
            collection_id = resp['record']
        else:
            resp = requests.get(f'{url}/c', json=data, headers=headers)
            collection_id = resp.json()[0]['record']

        # LIST THE BINS OF THE COLLECTION

        resp = requests.get(f'{url}/c/{collection_id}/bins',
                            json=data,
                            headers=headers)

        bin_id = [
            b['record'] for b in resp.json()
            if b['snippetMeta']['name'] == 'DATA'
        ]
        if bin_id:
            # If the bin exists, return it
            bin_id = bin_id[0]
        else:
            # If not (first run), create a bin with the initial data
            print('Creating a new bin...')
            headers.update({
                'X-Bin-Name': 'DATA',
                'Content-Type': 'application/json',
                'X-Collection-Id': collection_id
            })
            resp = requests.post(f'{url}/b',
                                 json=include_data,
                                 headers=headers)
            bin_id = resp.json()['metadata']['id']

        return bin_id

    def read_bin(self, bin_id):
        url = 'https://api.jsonbin.io/v3'
        headers = {'X-Master-Key': self.jsonbin_key}
        read_resp = requests.get(f'{url}/b/{bin_id}', headers=headers)
        return read_resp.json()

    def update_bin(self, bin_id, data):
        url = 'https://api.jsonbin.io/v3'
        headers = {
            'X-Master-Key': self.jsonbin_key,
            'Content-Type': 'application/json'
        }
        put_resp = requests.put(f'{url}/b/{bin_id}',
                                json=data,
                                headers=headers)
        return put_resp.json()
