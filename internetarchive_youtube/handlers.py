#!/usr/bin/env python
# coding: utf-8


class TimeLimitReached(Exception):
    pass


def alarm_handler(signum: int, _: object):
    print('Signal handler called with signal:', signum)
    raise TimeLimitReached(
        'The GitHub action is about to die. Terminating the job safely...')
