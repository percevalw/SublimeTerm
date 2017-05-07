# Copyright (C) 2016-2017 Perceval Wajsburt <perceval.wajsburt@gmail.com>
#
# This module is part of SublimeTerm and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

from unittest import TestCase
from sublimeterm.ansi_output_transcoder import ANSIOutputTranscoder


class TestANSIOutputTranscoder(TestCase):
    def test_normal_sequence(self):
        sm = ANSIOutputTranscoder()

        sm.decode("AAAAAA\nAAAAAA\x1b[3D\x1b[0Kok\nAAAAAA\x1b[A\n\n")

        expected_output1 = ('AAAAAA\nAAAok\nAAAAAA\n', 0, 20, 20, 20, 20)
        self.assertEqual(expected_output1, sm.pop_output(timeout=1))
