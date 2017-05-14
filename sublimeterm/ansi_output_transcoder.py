"""This implements an ANSI (VT100) terminal emulator as a subclass of screen.
PEXPECT LICENSE
    This license is approved by the OSI and FSF as GPL-compatible.
        http://opensource.org/licenses/isc-license.txt
    Original work Copyright (c) 2012, Noah Spurrier <noah@noah.org>
    Modified work Copyright 2016-2017 Perceval Wajsburt <perceval.wajsburt@gmail.com>
    PERMISSION TO USE, COPY, MODIFY, AND/OR DISTRIBUTE THIS SOFTWARE FOR ANY
    PURPOSE WITH OR WITHOUT FEE IS HEREBY GRANTED, PROVIDED THAT THE ABOVE
    COPYRIGHT NOTICE AND THIS PERMISSION NOTICE APPEAR IN ALL COPIES.
    THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
    WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
    MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
    ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
    WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
    ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
    OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
"""

# references:
#     http://en.wikipedia.org/wiki/ANSI_escape_code
#     http://www.retards.org/terminals/vt102.html
#     http://vt100.net/docs/vt102-ug/contents.html
#     http://vt100.net/docs/vt220-rm/
#     http://www.termsys.demon.co.uk/vtansi.htm

import logging
import string

from .fsm import *
from .output_transcoder import *


logger = logging.getLogger()


def log_debug(*args):
    logger.debug(" ".join(map(str, args)))

#
# The 'Do.*' functions are helper functions for the ANSI class.
#

__all__ = ['ANSIOutputTranscoder']


def DoEmit(fsm):
    screen = fsm.memory[0]
    screen.write(fsm.input_symbol)


def DoStartNumber(fsm):
    fsm.memory.append(fsm.input_symbol)


def DoBuildNumber(fsm):
    ns = fsm.memory.pop()
    ns = ns + fsm.input_symbol
    fsm.memory.append(ns)


def DoBackOne(fsm):
    screen = fsm.memory[0]
    screen.move_backward()


def DoBack(fsm):
    count = int(fsm.memory.pop())
    screen = fsm.memory[0]
    screen.move_backward(count)


def DoDownOne(fsm):
    screen = fsm.memory[0]
    screen.move_down()


def DoDown(fsm):
    count = int(fsm.memory.pop())
    screen = fsm.memory[0]
    screen.move_down(count)


def DoForwardOne(fsm):
    screen = fsm.memory[0]
    screen.move_forward()


def DoForward(fsm):
    count = int(fsm.memory.pop())
    screen = fsm.memory[0]
    screen.move_forward(count)


def DoUpReverse(fsm):
    screen = fsm.memory[0]
    screen.move_up()


def DoUpOne(fsm):
    screen = fsm.memory[0]
    screen.move_up()


def DoUp(fsm):
    count = int(fsm.memory.pop())
    screen = fsm.memory[0]
    screen.move_up(count)


def DoHome(fsm):
    c = int(fsm.memory.pop())
    r = int(fsm.memory.pop())
    screen = fsm.memory[0]
    screen.move_to(c, r)


def DoHomeOrigin(fsm):
    c = 1
    r = 1
    screen = fsm.memory[0]
    screen.move_to(c, r)


def DoGoX(fsm):
    c = int(fsm.memory.pop())
    screen = fsm.memory[0]
    screen.move_to(x=c)


def DoEraseDown(fsm):
    screen = fsm.memory[0]
    screen.erase_down()


def DoErase(fsm):
    arg = int(fsm.memory.pop())
    screen = fsm.memory[0]
    if arg == 0:
        screen.erase_down()
    elif arg == 1:
        screen.erase_up()
    elif arg == 2:
        screen.erase_screen()


def DoEraseEndOfLine(fsm):
    screen = fsm.memory[0]
    screen.erase_end_of_line()


def DoEraseLine(fsm):
    arg = int(fsm.memory.pop())
    screen = fsm.memory[0]
    if arg == 0:
        screen.erase_end_of_line()
    elif arg == 1:
        screen.erase_start_of_line()
    elif arg == 2:
        screen.erase_line()


def DoInsertSpaces(fsm):
    arg = int(fsm.memory.pop())
    screen = fsm.memory[0]
    screen.write(' ' * arg, insert_after=True)


def DoEraseForward(fsm):
    arg = int(fsm.memory.pop())
    screen = fsm.memory[0]
    screen.erase_forward(arg)


def DoEraseForwardOne(fsm):
    arg = 1
    screen = fsm.memory[0]
    screen.erase_forward(arg)


def DoEnableScroll(fsm):
    pass


#    screen = fsm.memory[0]
#   screen.scroll_screen()

def DoCursorSave(fsm):
    pass


#    screen = fsm.memory[0]
#   screen.cursor_save_attrs()

def DoCursorRestore(fsm):
    pass


#    screen = fsm.memory[0]
#    screen.cursor_restore_attrs()

def DoScrollRegion(fsm):
    pass


#    screen = fsm.memory[0]
#    r2 = int(fsm.memory.pop())
#    r1 = int(fsm.memory.pop())
#    screen.scroll_screen_rows (r1,r2)

def DoMode(fsm):
    pass


#    screen = fsm.memory[0]
#    mode = fsm.memory.pop() # Should be 4
# screen.setReplaceMode ()

def DoLog(fsm):
    pass


#    screen = fsm.memory[0]
#    fsm.memory = [screen]
#    fout = open ('log', 'a')
#    fout.write (fsm.input_symbol + ',' + fsm.current_state + '\n')
#    fout.close()

def DoModecrapL(fsm):
    arg = int(fsm.memory.pop())
    log_debug("MODECRAP L", arg)
    screen = fsm.memory[0]
    if arg == 1049:
        screen.switchASBOff()
    fsm.memory = [screen]


def DoModecrapH(fsm):
    arg = int(fsm.memory.pop())
    log_debug("MODECRAP H", arg)
    screen = fsm.memory[0]
    if arg == 1049:
        screen.switchASBOn()
    fsm.memory = [screen]


class ANSIOutputTranscoder(OutputTranscoder):
    """This class implements an ANSI (VT100) terminal.
    It is a stream filter that recognizes ANSI terminal
    escape sequences and maintains the state of a screen object. """

    def __init__(self, *args, **kwargs):
        OutputTranscoder.__init__(self, *args, **kwargs)
        # self.screen = screen (24,80)
        self.state = FSM('INIT', [self])

        self.state.set_default_transition(DoLog, 'INIT')
        self.state.add_transition_any('INIT', DoEmit, 'INIT')
        self.state.add_transition('\x1b', 'INIT', None, 'ESC')
        self.state.add_transition('\x08', 'INIT', DoBackOne, 'INIT')
        self.state.add_transition('\x07', 'INIT', None, 'INIT')
        self.state.add_transition_any('ESC', DoLog, 'INIT')
        self.state.add_transition('(', 'ESC', None, 'G0SCS')
        self.state.add_transition(')', 'ESC', None, 'G1SCS')
        self.state.add_transition_list('AB012', 'G0SCS', None, 'INIT')
        self.state.add_transition_list('AB012', 'G1SCS', None, 'INIT')
        self.state.add_transition('7', 'ESC', DoCursorSave, 'INIT')
        self.state.add_transition('8', 'ESC', DoCursorRestore, 'INIT')
        self.state.add_transition('M', 'ESC', DoUpReverse, 'INIT')
        self.state.add_transition('>', 'ESC', DoUpReverse, 'INIT')
        self.state.add_transition('<', 'ESC', DoUpReverse, 'INIT')
        self.state.add_transition('=', 'ESC', None, 'INIT')  # Selects application keypad.
        self.state.add_transition('#', 'ESC', None, 'GRAPHICS_POUND')
        self.state.add_transition_any('GRAPHICS_POUND', None, 'INIT')
        """
        ESC [ sequences
        """
        # ELB means Escape Left Bracket. That is ^[[
        self.state.add_transition('[', 'ESC', None, 'ELB')
        self.state.add_transition('H', 'ELB', DoHomeOrigin, 'INIT')
        self.state.add_transition('D', 'ELB', DoBackOne, 'INIT')
        self.state.add_transition('B', 'ELB', DoDownOne, 'INIT')
        self.state.add_transition('C', 'ELB', DoForwardOne, 'INIT')
        self.state.add_transition('P', 'ELB', DoEraseForwardOne, 'INIT')
        self.state.add_transition('A', 'ELB', DoUpOne, 'INIT')
        self.state.add_transition('J', 'ELB', DoEraseDown, 'INIT')
        self.state.add_transition('K', 'ELB', DoEraseEndOfLine, 'INIT')
        self.state.add_transition('r', 'ELB', DoEnableScroll, 'INIT')
        self.state.add_transition('m', 'ELB', self.do_sgr, 'INIT')
        self.state.add_transition('?', 'ELB', None, 'MODECRAP')
        self.state.add_transition_list(string.digits, 'ELB', DoStartNumber, 'NUMBER_1_ELB')
        self.state.add_transition_list(string.digits, 'NUMBER_1_ELB', DoBuildNumber, 'NUMBER_1_ELB')
        self.state.add_transition('D', 'NUMBER_1_ELB', DoBack, 'INIT')
        self.state.add_transition('B', 'NUMBER_1_ELB', DoDown, 'INIT')
        self.state.add_transition('C', 'NUMBER_1_ELB', DoForward, 'INIT')
        self.state.add_transition('G', 'NUMBER_1_ELB', DoGoX, 'INIT')
        self.state.add_transition('A', 'NUMBER_1_ELB', DoUp, 'INIT')
        self.state.add_transition('P', 'NUMBER_1_ELB', DoEraseForward, 'INIT')
        self.state.add_transition('J', 'NUMBER_1_ELB', DoErase, 'INIT')
        self.state.add_transition('K', 'NUMBER_1_ELB', DoEraseLine, 'INIT')
        self.state.add_transition('l', 'NUMBER_1_ELB', DoMode, 'INIT')
        self.state.add_transition('@', 'NUMBER_1_ELB', DoInsertSpaces, 'INIT')
        # It gets worse... the 'm' code can have infinite number of
        # number;number;number before it. I've never seen more than two,
        # but the specs say it's allowed. crap!
        self.state.add_transition('m', 'NUMBER_1_ELB', self.do_sgr, 'INIT')
        # LED control. Same implementation problem as 'm' code.
        self.state.add_transition('q', 'NUMBER_1_ELB', self.do_decsca, 'INIT')
        # \E[?47h switch to alternate screen
        # \E[?47l restores to normal screen from alternate screen.
        self.state.add_transition_list(string.digits, 'MODECRAP', DoStartNumber, 'MODECRAP_NUM')
        self.state.add_transition_list(string.digits, 'MODECRAP', DoStartNumber, 'MODECRAP_NUM')
        self.state.add_transition_list(string.digits, 'MODECRAP_NUM', DoBuildNumber, 'MODECRAP_NUM')
        self.state.add_transition('l', 'MODECRAP_NUM', DoModecrapL, 'INIT')
        self.state.add_transition('h', 'MODECRAP_NUM', DoModecrapH, 'INIT')

        """
        ESC > sequences
        """
        self.state.add_transition('>', 'ELB', None, 'ELC')
        self.state.add_transition('c', 'NUMBER_1_ELB', None, 'INIT')
        self.state.add_transition('c', 'ELC', None, 'INIT')
        self.state.add_transition_list(string.digits, 'ELC', DoStartNumber, 'NUMBER_1_ELC')
        self.state.add_transition_list(string.digits, 'NUMBER_1_ELC', DoBuildNumber, 'NUMBER_1_ELC')

        # RM   Reset Mode                Esc [ Ps l                   none
        self.state.add_transition(';', 'NUMBER_1_ELB', None, 'SEMICOLON')
        self.state.add_transition_any('SEMICOLON', DoLog, 'INIT')
        self.state.add_transition_list(string.digits, 'SEMICOLON', DoStartNumber, 'NUMBER_2_ELC')
        self.state.add_transition_list(string.digits, 'NUMBER_2_ELC', DoBuildNumber, 'NUMBER_2_ELC')
        self.state.add_transition_any('NUMBER_2_ELC', DoLog, 'INIT')
        self.state.add_transition('H', 'NUMBER_2_ELC', DoHome, 'INIT')
        self.state.add_transition('f', 'NUMBER_2_ELC', DoHome, 'INIT')
        self.state.add_transition('r', 'NUMBER_2_ELC', DoScrollRegion, 'INIT')
        # It gets worse... the 'm' code can have infinite number of
        # number;number;number before it. I've never seen more than two,
        # but the specs say it's allowed. crap!
        self.state.add_transition('m', 'NUMBER_2_ELC', self.do_sgr, 'INIT')
        # LED control. Same problem as 'm' code.
        self.state.add_transition('q', 'NUMBER_2_ELC', self.do_decsca, 'INIT')
        self.state.add_transition(';', 'NUMBER_2_ELC', None, 'SEMICOLON_X')

        # Create a state for 'q' and 'm' which allows an infinite number of ignored numbers
        self.state.add_transition_any('SEMICOLON_X', DoLog, 'INIT')
        self.state.add_transition_list(string.digits, 'SEMICOLON_X', DoStartNumber, 'NUMBER_X')
        self.state.add_transition_list(string.digits, 'NUMBER_X', DoBuildNumber, 'NUMBER_X')
        self.state.add_transition_any('NUMBER_X', DoLog, 'INIT')
        self.state.add_transition('m', 'NUMBER_X', self.do_sgr, 'INIT')
        self.state.add_transition('q', 'NUMBER_X', self.do_decsca, 'INIT')
        self.state.add_transition(';', 'NUMBER_X', None, 'SEMICOLON_X')

    def decode(self, s):
        """Process text, writing it to the virtual screen while handling
        ANSI escape codes.
        """
        if isinstance(s, bytes):
            s = s.decode('UTF-8')
        self.begin_sequence()
        self.state.process_list(s)
        self.end_sequence()

    @staticmethod
    def do_sgr(fsm):
        """Select Graphic Rendition, e.g. color. """
        screen = fsm.memory[0]
        fsm.memory = [screen]

    @staticmethod
    def do_decsca(fsm):
        """Select character protection attribute. """
        screen = fsm.memory[0]
        fsm.memory = [screen]
