#!/usr/bin/env python
# coding: utf-8

import re
import string
from pathlib import Path


def clean_fname(file_name):
    illegal = [
        x for x in string.punctuation + string.whitespace if x not in '._-'
    ]

    fname = Path(file_name).stem

    matches = re.search(r'\s\[(?<=\[).+?(?=\])\]', fname)
    if matches:
        fname = fname.replace(matches[0], '')
    fname = re.sub(' {2,}', ' ', fname)

    clean_fname = ''.join([
        x if x not in illegal and x in string.printable else '-' for x in fname
    ])
    clean_fname = re.sub('-{2,}', '-', clean_fname)

    if clean_fname.endswith('-'):
        clean_fname = clean_fname[:-1]

    clean_fname = f'{clean_fname}{Path(file_name).suffix}'
    return clean_fname


if __name__ == '__main__':
    clean_fname()
