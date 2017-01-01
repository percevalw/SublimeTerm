#!/usr/bin/env python

import fcntl
import logging
import os
import select
import signal
import struct
import subprocess
import time
from threading import Lock, Thread

from .ansi_output_transcoder import *
from .input_transcoder import *

try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty  # python 3.x


logger = logging.getLogger()


def log_debug(*args):
    logger.debug(" ".join(map(str, args)))

__all__ = ['ProcessController']

try:
    # log_debug("stop potentially-existing ProcessController...")
    c = ProcessController.instance.close()
except:
    # log_debug("and there was none")
    pass
else:
    # log_debug("and there was one")
    pass


class ProcessController:
    instance = None

    def __new__(cls, input_transcoder, output_transcoder):
        if isinstance(cls.instance, cls):
            cls.instance.close()
        cls.instance = object.__new__(cls)
        return cls.instance

    def __init__(self, input_transcoder, output_transcoder):
        self.master = None
        self.slave = None
        self.process = None

        self.input_transcoder = input_transcoder
        self.output_transcoder = output_transcoder

        self.mutex = Lock()
        self.read_thread = None
        self.write_thread = None
        self.stop = False

    def start(self, command):
        """ Create the PTY """
        self.spawn(command)

        """ Loops """
        self.read_thread = Thread(target=self.keep_reading)
        self.write_thread = Thread(target=self.keep_writing)

        self.read_thread.start()
        self.write_thread.start()

    def close(self):
        self.stop = True

        try:
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
        except:
            log_debug("Must already be dead")
        else:
            log_debug("Successfully killed")
        ProcessController.instance = None

    def spawn(self, command):
        self.master, self.slave = os.openpty()
        self.process = subprocess.Popen(command,
                                        stdin=self.slave,
                                        stdout=self.slave,
                                        stderr=self.slave,
                                        preexec_fn=os.setsid)

    def keep_reading(self):
        while True:
            if self.stop:
                break
            readable, writable, executable = select.select([self.master], [], [], 5)
            if readable:
                """ We read the new content """
                data = os.read(self.master, 1024)
                text = data.decode('UTF-8')
                log_debug("RAW", repr(text))
                log_debug("PID", os.getenv('BASHPID'))
                self.output_transcoder.decode(text)
            #                log_debug("{} >> {}".format(int(time.time()), repr(text)))

    def keep_writing(self):
        while True:
            if self.stop:
                break
            readable, writable, executable = select.select([], [self.master], [], 5)
            if writable:
                try:
                    (input_type, content) = self.input_transcoder.pop_input(timeout=1)
                except Empty:
                    pass
                else:
                    if input_type == 0:
                        log_debug("Sending input\n<< {}".format(repr(content)))
                        data = content.encode('UTF-8')
                        #                        data = bytes(chaine, 'iso-8859-15')
                        while data:
                            chars_written = os.write(self.master, data)
                            data = data[chars_written:]
                    elif input_type == 1:
                        (signal_type, signal_content) = content
                        t = fcntl.ioctl(self.master, signal_type, signal_content)
                        log_debug(struct.unpack('HHHH', t))
                    elif input_type == 2:
                        os.killpg(os.getpgid(self.process.pid), content)
                        log_debug("SENDING SIGNAL TO PROCESS", content)


def main():
    input_transcoder = InputTranscoder()
    output_transcoder = ANSIOutputTranscoder()
    pty = ProcessController(input_transcoder, output_transcoder)
    pty.start()
    time.sleep(3)
    input_transcoder.write("ls\n")
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        log_debug("\nINTERRUPTION !")
        pty.close()


if __name__ == '__main__':
    main()
