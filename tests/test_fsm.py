# Copyright (C) 2016-2017 Perceval Wajsburt <perceval.wajsburt@gmail.com>
#
# This module is part of SublimeTerm and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

from unittest import TestCase
from sublimeterm.fsm import FSM
import string


class ComputeException(Exception):
    pass


def BeginBuildNumber(fsm):
    fsm.memory.append(fsm.input_symbol)


def BuildNumber(fsm):
    s = fsm.memory.pop()
    s = s + fsm.input_symbol
    fsm.memory.append(s)


def EndBuildNumber(fsm):
    s = fsm.memory.pop()
    fsm.memory.append(int(s))


def DoOperator(fsm):
    ar = fsm.memory.pop()
    al = fsm.memory.pop()
    if fsm.input_symbol == '+':
        fsm.memory.append(al + ar)
    elif fsm.input_symbol == '-':
        fsm.memory.append(al - ar)
    elif fsm.input_symbol == '*':
        fsm.memory.append(al * ar)
    elif fsm.input_symbol == '/':
        fsm.memory.append(al / ar)


def DoEqual(fsm):
    result = fsm.memory.pop()
    store = fsm.memory.pop()
    store[0] = result


def Error(fsm):
    raise ComputeException()


class TestANSIOutputTranscoder(TestCase):
    def test_normal_sequence(self):

        result_store = [None]

        f = FSM('INIT', [result_store])
        f.set_default_transition(Error, 'INIT')
        f.add_transition_any('INIT', None, 'INIT')
        f.add_transition('=', 'INIT', DoEqual, 'INIT')
        f.add_transition_list(string.digits, 'INIT', BeginBuildNumber, 'BUILDING_NUMBER')
        f.add_transition_list(string.digits, 'BUILDING_NUMBER', BuildNumber, 'BUILDING_NUMBER')
        f.add_transition_list(string.whitespace, 'BUILDING_NUMBER', EndBuildNumber, 'INIT')
        f.add_transition_list('+-*/', 'INIT', DoOperator, 'INIT')
        f.process_list('167 3 2 2 * * * 1 - =')

        self.assertEqual(result_store[0], 2003)

