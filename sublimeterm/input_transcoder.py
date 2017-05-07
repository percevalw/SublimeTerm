# Copyright (C) 2016-2017 Perceval Wajsburt <perceval.wajsburt@gmail.com>
#
# This module is part of SublimeTerm and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

import logging
import struct
import termios

from .utils import *

try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty  # python 3.x

logger = logging.getLogger()


def log_debug(*args):
    logger.debug(" ".join(map(str, args)))


__all__ = ['InputTranscoder']


class InputTranscoder():
    def __init__(self):
        self.input_queue = Queue()

    def pop_input(self, timeout):
        try:
            i = self.input_queue.get(timeout=timeout)
        except:
            raise Empty
        else:
            return i

    def write(self, content):
        self.input_queue.put((0, content))

    def enter(self):
        self.input_queue.put((0, "\n"))

    def set_size(self, w, h, pw, ph):
        s = struct.pack('HHHH', h, w, ph, pw)
        log_debug("SIZE TO BE SENT", struct.unpack('HHHH', s))
        self.input_queue.put((1, (termios.TIOCSWINSZ, s)))

    #        self.input_queue.put((2, signal.SIGWINCH))

    def move(self, rel):

        s = ""
        if rel > 0:
            s = ''.join([SpecialChar.RIGHT for s in range(rel)])
        elif rel < 0:
            s = ''.join([SpecialChar.LEFT for s in range(-rel)])
        else:
            return
        self.input_queue.put((0, s))

    def erase(self, n=1):
        if n <= 0:
            return
        s = ''.join(['\x08' for s in range(n)])
        self.input_queue.put((0, s))


# [0, 1, 2, '\n'] -> 4 [a, b, c, d, '\n'] -> 5
# cursor = 0, cursor += 6 : y += 1 et x = x - (len(line) - 1) = 6 - 4 + 1 = 3
