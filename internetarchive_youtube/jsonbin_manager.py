#!/usr/bin/env python
# coding: utf-8

import requests

BASE_URL = 'https://api.jsonbin.io/v3'
COLLECTION_NAME = 'yt_archive_sync_collection'
TIMEOUT = 30


class NoDataToInclude(Exception):
    """Raised when there is no data to include."""


class MissingMasterKey(Exception):
    """Raised when the master key is missing."""


class JSONBinError(Exception):
    """Raised when the JSONBin API returns an error response."""


class JSONBin:
    """JSONBin manager."""

    def __init__(self, jsonbin_key: str, no_logs: bool = False):
        """Initialize the JSONBin manager.

        Args:
            jsonbin_key: The JSONBin master key.
            no_logs: Whether to print logs or not.
        """
        self.jsonbin_key = jsonbin_key
        self.no_logs = no_logs

    @property
    def _auth(self) -> dict:
        return {'X-Master-Key': self.jsonbin_key}

    def _check(self, resp: requests.Response) -> object:
        """Raise on HTTP error or API-level error message."""
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and 'message' in data:
            raise JSONBinError(data['message'])
        return data

    def handle_collection_bins(self, include_data=None) -> str:
        """Return the DATA bin ID, creating the collection/bin if needed.

        Args:
            include_data: Initial records to store when creating a new bin.

        Returns:
            The bin ID string.
        """
        if not self.jsonbin_key:
            raise MissingMasterKey("The secret JSONBIN token can't be None!")

        # --- Find or create the collection ---
        collections = self._check(
            requests.get(f'{BASE_URL}/c', headers=self._auth, timeout=TIMEOUT))

        collection_id = None
        for col in collections:
            if col.get('collectionMeta', {}).get('name') == COLLECTION_NAME:
                collection_id = col['record']
                break

        if not collection_id:
            data = self._check(
                requests.post(f'{BASE_URL}/c',
                              json={},
                              headers={
                                  **self._auth,
                                  'X-Collection-Name': COLLECTION_NAME
                              },
                              timeout=TIMEOUT))
            collection_id = data['record']

        # --- Find or create the DATA bin ---
        bins = self._check(
            requests.get(f'{BASE_URL}/c/{collection_id}/bins',
                         headers=self._auth,
                         timeout=TIMEOUT))

        bin_id = None
        for b in bins:
            if b.get('snippetMeta', {}).get('name') == 'DATA':
                bin_id = b['record']
                break

        if not bin_id:
            if not include_data:
                raise NoDataToInclude
            if not self.no_logs:
                print('Creating a new bin...')
            data = self._check(
                requests.post(f'{BASE_URL}/b',
                              json=include_data,
                              headers={
                                  **self._auth,
                                  'Content-Type': 'application/json',
                                  'X-Bin-Name': 'DATA',
                                  'X-Collection-Id': collection_id,
                              },
                              timeout=TIMEOUT))
            bin_id = data['metadata']['id']

        return bin_id

    def read_bin(self, bin_id: str) -> dict:
        """Read a bin and return the full API response.

        Args:
            bin_id: The bin ID.

        Returns:
            The full response dict with 'record' and 'metadata' keys.
        """
        return self._check(
            requests.get(f'{BASE_URL}/b/{bin_id}',
                         headers=self._auth,
                         timeout=TIMEOUT))

    def update_bin(self, bin_id: str, data) -> dict:
        """Replace the bin contents.

        Args:
            bin_id: The bin ID.
            data: The new data to store.

        Returns:
            The API response dict.
        """
        return self._check(
            requests.put(f'{BASE_URL}/b/{bin_id}',
                         json=data,
                         headers={
                             **self._auth,
                             'Content-Type': 'application/json',
                             'X-Bin-Versioning': 'false',
                         },
                         timeout=TIMEOUT))
