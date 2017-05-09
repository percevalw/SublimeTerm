# Copyright (C) 2016-2017 Perceval Wajsburt <perceval.wajsburt@gmail.com>
#
# This module is part of SublimeTerm and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

from unittest import TestCase
from sublimeterm.process_controller import ProcessController

from sublimeterm.ansi_output_transcoder import *
from sublimeterm.input_transcoder import *
import time


class TestProcessController(TestCase):
    def test_no_input(self):
        input_transcoder = InputTranscoder()
        output_transcoder = ANSIOutputTranscoder()
        with ProcessController(input_transcoder, output_transcoder, command=["echo", 'Hello World']):
            time.sleep(3)
            expected_result = ('Hello World\n', 0, 12, 12, 12, 12)
            self.assertEqual(expected_result, output_transcoder.pop_output(timeout=2))

    def test_dumb_input(self):
        input_transcoder = InputTranscoder()
        output_transcoder = ANSIOutputTranscoder()
        with ProcessController(input_transcoder, output_transcoder, command=["echo", 'Hello World']):
            time.sleep(3)
            input_transcoder.write("DUMB INPUT")
            expected_result = ('Hello World\n', 0, 12, 12, 12, 12)
            self.assertEqual(expected_result, output_transcoder.pop_output(timeout=2))

    def test_sh(self):
        input_transcoder = InputTranscoder()
        output_transcoder = ANSIOutputTranscoder()
        with ProcessController(input_transcoder, output_transcoder, command=["/bin/sh"], env={"PS1": "BASH$"}):
            time.sleep(3)
            self.assertRegexpMatches(output_transcoder.pop_output(timeout=2)[0], "BASH\$")
            input_transcoder.write("pwd\n")
            time.sleep(2)
            self.assertIn("SublimeTerm", output_transcoder.pop_output(timeout=2)[0])