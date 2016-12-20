#!/usr/bin/env python
# coding: utf8

import sys, os, subprocess, time, signal, select, struct, termios, fcntl
from threading import Event, Lock, Thread

try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty  # python 3.x

from .log import *


#def log(*args):
#    return


class SpecialChar:
    NEW_LINE = '\n'
    TAB = '\t'
    BEL = '\x07'
    BACKSPACE = '\x08'
    UP = '\x1BOA'
    DOWN = '\x1BOB'
    LEFT = '\x1BOD'
    RIGHT = '\x1BOC'  # '\x1B[C'
    ESCAPE = '\x1B'
