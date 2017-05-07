# Copyright (C) 2016-2017 Perceval Wajsburt <perceval.wajsburt@gmail.com>
#
# This module is part of SublimeTerm and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

from unittest import TestCase
from sublimeterm.output_transcoder import OutputTranscoder


class TestOutputTranscoder(TestCase):
    def test_normal_sequence(self):
        sm = OutputTranscoder()

        sm.begin_sequence()
        sm.write("the cat is angry")
        sm.crlf()
        sm.write("the dog is not happy")
        sm.move_backward(6)
        sm.erase_start_of_line()
        sm.cr()
        sm.write("the turtle is")
        sm.move_up(1)
        sm.erase_line()
        sm.end_sequence()

        expected_output1 = ('\nthe turtle is  happy', 0, 0, 21, 21, 21)
        self.assertEqual(expected_output1, sm.pop_output(timeout=1))

        sm.begin_sequence()
        sm.write("hello world")
        sm.cr()
        sm.write("hi", insert_after=True)
        sm.move_forward(2)
        sm.erase_end_of_line()
        sm.end_sequence()

        expected_output2 = ('hi', 0, 2, 2, 2, 23)
        self.assertEqual(expected_output2, sm.pop_output(timeout=1))

    def test_asb_sequence(self):
        sm = OutputTranscoder()

        sm.begin_sequence()
        sm.write("the cat")
        sm.end_sequence()

        expected_output1 = ('the cat', 0, 7, 7, 7, 7)
        self.assertEqual(expected_output1, sm.pop_output(timeout=1))

        sm.begin_sequence()
        sm.switchASBOn()
        sm.move_forward(3)
        sm.move_down(3)
        sm.write_char("O")
        sm.end_sequence()

        expected_output2 = ('\n\n\n          O', 7, 21, 21, 14, 21)
        self.assertEqual(expected_output2, sm.pop_output(timeout=1))

        sm.begin_sequence()
        sm.switchASBOff()
        sm.end_sequence()
        expected_output2 = ('the cat', 0, 7, 7, -14, 7)
        self.assertEqual(expected_output2, sm.pop_output(timeout=1))
