#!/usr/bin/env python

from threading import Lock

__all__ = ['log']

log_lock = Lock()

def log(*args):
    return
    log_lock.acquire()
    print(*args)
    log_lock.release()
