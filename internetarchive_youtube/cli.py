#!/usr/bin/env python
# coding: utf-8
"""Command line interface for Internetarchive-YouTube Sync."""

import argparse
import io
import json
import os
import random
import signal
from pathlib import Path

import requests
from dotenv import load_dotenv

from internetarchive_youtube.archive_youtube import ArchiveYouTube
from internetarchive_youtube.create_collection import CreateCollection


class TimeLimitReached(Exception):
    """Raised when the time limit is reached."""


def _alarm_handler(signum: int, _: object):
    """Signal handler for SIGALRM.

    Raises:
        TimeLimitReached: When the time limit is reached.
    """
    print('Signal handler called with signal:', signum)
    raise TimeLimitReached(
        'The GitHub action is about to die. Terminating the job safely...')


def _create_collection(no_logs: bool = False) -> None:
    """Creates a collection from the channels list.

    Args:
        no_logs: Whether to print logs.
    """
    channels = os.getenv('CHANNELS')
    if not channels:
        raise TypeError('`CHANNELS` cannot be empty!')

    if channels.startswith('http'):
        channels = requests.get(channels).text

    elif Path(channels).exists():
        with open(channels) as f:
            channels = f.read()

    try:
        channels = json.loads(channels).items()
    except json.decoder.JSONDecodeError:
        channels = [tuple(x.split(': ')) for x in channels.strip().split('\n')]

    random.shuffle(channels)

    for channel in channels:
        if not no_logs:
            print(f'Current channel: {channel}')
        cc = CreateCollection(channel[0], channel[1], no_logs=no_logs)
        _ = cc.create_collection()


def _opts() -> argparse.Namespace:
    """Parses the command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument('-p',
                        '--prioritize',
                        help='Comma-separated list of channel names to '
                        'prioritize when processing videos.',
                        type=str)
    parser.add_argument('-s',
                        '--skip-list',
                        help='Comma-separated list of channel names to skip.',
                        type=str)
    parser.add_argument('-f',
                        '--force-refresh',
                        help='Refresh the database after every video ('
                        'Can slow down the workflow significantly, but '
                        'is useful when running multiple concurrent jobs).',
                        action='store_true')
    parser.add_argument('-t',
                        '--timeout',
                        help='Kill the job after n hours (default: 5).',
                        type=float,
                        default=5)
    parser.add_argument('-n',
                        '--no-logs',
                        help='Don\'t print any log messages.',
                        action='store_true')
    parser.add_argument('-a',
                        '--add-channel',
                        help='Add a channel interactively to the list of '
                        'channels to archive.',
                        action='store_true')
    parser.add_argument('-c',
                        '--channels-file',
                        help='Path to the channels list file to use if the '
                        'environment variable `CHANNELS` is not set ('
                        'default: ~/.yt_channels.txt).',
                        type=str)
    parser.add_argument('-S',
                        '--show-channels',
                        help='Show the list of channels in the channels file.',
                        action='store_true')
    parser.add_argument('-C',
                        '--create-collection',
                        help='Creates/appends to the backend database from '
                        'the channels list.',
                        action='store_true')
    parser.add_argument(
        '-m',
        '--multithreading',
        help='Enables processing multiple videos concurrently.',
        action='store_true')
    parser.add_argument('-T',
                        '--threads',
                        help='Number of threads to use when multithreading is '
                        'enabled. Defaults to the optimal maximum number of '
                        'workers.',
                        type=int)
    parser.add_argument(
        '-k',
        '--keep-failed-uploads',
        help='Keep the files of failed uploads on the local disk.',
        action='store_true')
    parser.add_argument('-i',
                        '--ignore-video-ids',
                        help='Comma-separated list or a path to a file '
                        'containing a list of video ids to ignore.',
                        type=str)
    parser.add_argument(
        '-A',
        '--use-aria2c',
        help='Use external downloader, aria2c '
        '(can significantly speed up download).',
        action='store_true')
    return parser.parse_args()


def main() -> None:
    """Main function."""
    load_dotenv()
    args = _opts()

    signal.signal(signal.SIGALRM, _alarm_handler)
    timeout = int(args.timeout * 3600)

    if args.create_collection:
        _create_collection(no_logs=args.no_logs)

    if not args.channels_file:
        args.channels_file = f'{Path.home()}/.yt_channels.txt'
        if not os.getenv('CHANNELS'):
            os.environ['CHANNELS'] = args.channels_file

    if args.show_channels:
        chs_file = Path(args.channels_file)
        print('-' * 80)
        if not os.getenv('CHANNELS'):
            if not chs_file.exists():
                print('Nothing to show. Add channels to the channels '
                      'file first!')
            else:
                with open(chs_file) as f:
                    print(f.read())
            return
        elif args.show_channels and os.getenv('CHANNELS'):
            if chs_file.exists():
                with open(chs_file) as f:
                    print(f.read())
            else:
                print(os.environ['CHANNELS'])
        print('-' * 80)
        if chs_file.exists():
            print(f'Channels list file path: {chs_file}')
        return

    if args.add_channel:
        if os.getenv('CHANNELS'):
            if not Path(os.environ['CHANNELS']).exists():
                raise TypeError(
                    'Environment variable `CHANNELS` is set, but is not a '
                    'file path! Can only add channels with `--add-channel` '
                    'if `CHANNELS` is a file path.')
        with open(args.channels_file, 'a+') as f:
            f.seek(0, 0)
            if f.read():
                f.seek(0, io.SEEK_END)
                f.write('\n')
            channel_name = input('Channel name: ').replace(' ', '_').strip('_')
            channel_url = input('Channel URL: ')
            f.write(f'{channel_name}: {channel_url}')
        return

    if Path(args.channels_file).exists() and not args.no_logs:
        print(f'Using channels list in: {args.channels_file}')

    if args.prioritize:
        args.prioritize = args.prioritize.split(',')
    if args.skip_list:
        args.skip_list = args.skip_list.split(',')
    if args.ignore_video_ids:
        if Path(args.ignore_video_ids).exists():
            with open(args.ignore_video_ids) as f:
                args.ignore_video_ids = f.read().strip()
        args.ignore_video_ids = args.ignore_video_ids.split(',')

    try:
        signal.alarm(timeout)
        ayt = ArchiveYouTube(prioritize=args.prioritize,
                             skip_list=args.skip_list,
                             force_refresh=args.force_refresh,
                             no_logs=args.no_logs,
                             multithreading=args.multithreading,
                             threads=args.threads,
                             keep_failed_uploads=args.keep_failed_uploads,
                             ignore_video_ids=args.ignore_video_ids,
                             use_aria2c=args.use_aria2c)
        ayt.run()
    except TimeLimitReached:
        return


if __name__ == '__main__':
    main()
