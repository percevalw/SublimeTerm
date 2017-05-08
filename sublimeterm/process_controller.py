# Copyright (C) 2016-2017 Perceval Wajsburt <perceval.wajsburt@gmail.com>
#
# This module is part of SublimeTerm and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

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

    def __new__(cls, input_transcoder, output_transcoder, command=None, cwd=None, env=None):
        if isinstance(cls.instance, cls):
            cls.instance.close()
        cls.instance = object.__new__(cls)
        return cls.instance

    def __init__(self, input_transcoder, output_transcoder, command=None, cwd=None, env=None):
        self.master = None
        self.slave = None
        self.process = None

        self.input_transcoder = input_transcoder
        self.output_transcoder = output_transcoder

        self.command = command
        self.cwd = cwd
        self.env = env

        self.mutex = Lock()
        self.read_thread = None
        self.write_thread = None
        self.stop = False

    def __enter__(self):
        """Enter the process controller running scope

        with statement is the recommended way to launsh since
        it closes the process no matter what happens in the with
        statement body
        """
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Enter the process controller running scope

        with statement is the recommended way to launsh since
        it closes the process no matter what happens in the with
        statement body
        """
        self.close()

    def start(self):
        """Start the process controller
        
        Creates the threads and launsh the process
        
        Arguments:
            command {list} -- command list for the process (ex: ['ls', '-la'])
        """
        # Create the PTY
        self.spawn(self.command, self.cwd, self.env)

        # Loops
        self.read_thread = Thread(target=self.keep_reading)
        self.write_thread = Thread(target=self.keep_writing)

        self.read_thread.start()
        self.write_thread.start()

    def close(self):
        """Stops the process controller
        
        Kill the process
        """
        self.stop = True
        try:
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
        except ProcessLookupError:
            log_debug("Must already be dead")
        else:
            log_debug("Successfully killed")
        ProcessController.instance = None

    def spawn(self, command, cwd, env):
        """Starts the process
        
        Spawn a new process and register the listeners on it
        
        Arguments:
            command {list} -- command list for the process (ex: ['ls', '-la'])
        """

        child_env = os.environ.copy()
        child_env.update(env if env is not None else {})

        self.master, self.slave = os.openpty()
        self.process = subprocess.Popen(command,
                                        stdin=self.slave,
                                        stdout=self.slave,
                                        stderr=self.slave,
                                        preexec_fn=os.setsid,
                                        cwd=cwd,
                                        env=child_env)

    def keep_reading(self):
        """Output thread method for the process
        
        Sends the process output to the ViewController (through OutputTranscoder)
        """
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
        """Input thread method for the process
        
        Sends the user inputs (from InputTranscoder) to the process
        """
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
