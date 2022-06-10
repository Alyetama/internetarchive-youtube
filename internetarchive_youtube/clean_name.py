#!/usr/bin/env python
# coding: utf-8

import re
import string
import sys
from pathlib import Path


def clean_fname(file_name):
    illegal = [
        x for x in string.punctuation + string.whitespace if x not in '_-'
    ]

    fname = Path(file_name).name

    matches = re.search(r'\s\[(?<=\[).+?(?=\])\]', fname)  # noqa
    if matches:
        fname = fname.replace(matches[0], '')
    fname = re.sub(' {2,}', ' ', fname)

    clean_name = ''.join([
        x if x not in illegal and x in string.printable else '-' for x in fname
    ])
    clean_name = re.sub('-{2,}', '-', clean_name)

    if clean_name.endswith('-'):
        clean_name = clean_name[:-1]
    return clean_name


if __name__ == '__main__':
    print(clean_fname(sys.argv[1]))
