'''This implements an ANSI (VT100) terminal emulator as a subclass of screen.
PEXPECT LICENSE
	This license is approved by the OSI and FSF as GPL-compatible.
		http://opensource.org/licenses/isc-license.txt
	Copyright (c) 2012, Noah Spurrier <noah@noah.org>
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
'''

# references:
#	 http://en.wikipedia.org/wiki/ANSI_escape_code
#	 http://www.retards.org/terminals/vt102.html
#	 http://vt100.net/docs/vt102-ug/contents.html
#	 http://vt100.net/docs/vt220-rm/
#	 http://www.termsys.demon.co.uk/vtansi.htm

from .fsm import *
from .output_transcoder import *
import string

#
# The 'Do.*' functions are helper functions for the ANSI class.
#

__all__ = ['ANSIOutputTranscoder']

def DoEmit (fsm):

	screen = fsm.memory[0]
	screen.write(fsm.input_symbol)

def DoStartNumber (fsm):

	fsm.memory.append (fsm.input_symbol)

def DoBuildNumber (fsm):

	ns = fsm.memory.pop()
	ns = ns + fsm.input_symbol
	fsm.memory.append (ns)

def DoBackOne (fsm):

	screen = fsm.memory[0]
	screen.move_backward ()

def DoBack (fsm):

	count = int(fsm.memory.pop())
	screen = fsm.memory[0]
	screen.move_backward (count)

def DoDownOne (fsm):

	screen = fsm.memory[0]
	screen.move_down ()

def DoDown (fsm):

	count = int(fsm.memory.pop())
	screen = fsm.memory[0]
	screen.move_down (count)

def DoForwardOne (fsm):

	screen = fsm.memory[0]
	screen.move_forward ()

def DoForward (fsm):

	count = int(fsm.memory.pop())
	screen = fsm.memory[0]
	screen.move_forward (count)

def DoUpReverse (fsm):

	screen = fsm.memory[0]
	screen.move_up()

def DoUpOne (fsm):

	screen = fsm.memory[0]
	screen.move_up ()

def DoUp (fsm):

	count = int(fsm.memory.pop())
	screen = fsm.memory[0]
	screen.move_up (count)

def DoHome (fsm):

	c = int(fsm.memory.pop())
	r = int(fsm.memory.pop())
	screen = fsm.memory[0]
	screen.move_to (r,c)

def DoHomeOrigin (fsm):

	c = 1
	r = 1
	screen = fsm.memory[0]
	screen.move_to (r,c)

def DoEraseDown (fsm):

	screen = fsm.memory[0]
	screen.erase_down()

def DoErase (fsm):

	arg = int(fsm.memory.pop())
	screen = fsm.memory[0]
	if arg == 0:
		screen.erase_down()
	elif arg == 1:
		screen.erase_up()
	elif arg == 2:
		screen.erase_screen()

def DoEraseEndOfLine (fsm):

	screen = fsm.memory[0]
	screen.erase_end_of_line()

def DoEraseLine (fsm):

	arg = int(fsm.memory.pop())
	screen = fsm.memory[0]
	if arg == 0:
		screen.erase_end_of_line()
	elif arg == 1:
		screen.erase_start_of_line()
	elif arg == 2:
		screen.erase_line()

def DoEnableScroll (fsm):
	pass
#	screen = fsm.memory[0]
 #   screen.scroll_screen()

def DoCursorSave (fsm):
	pass
#	screen = fsm.memory[0]
#   screen.cursor_save_attrs()

def DoCursorRestore (fsm):
	pass
#	screen = fsm.memory[0]
#	screen.cursor_restore_attrs()

def DoScrollRegion (fsm):
	pass

#	screen = fsm.memory[0]
#	r2 = int(fsm.memory.pop())
#	r1 = int(fsm.memory.pop())
#	screen.scroll_screen_rows (r1,r2)

def DoMode (fsm):
	pass
#	screen = fsm.memory[0]
#	mode = fsm.memory.pop() # Should be 4
	# screen.setReplaceMode ()

def DoLog (fsm):
	pass
#	screen = fsm.memory[0]
#	fsm.memory = [screen]
#	fout = open ('log', 'a')
#	fout.write (fsm.input_symbol + ',' + fsm.current_state + '\n')
#	fout.close()

class ANSIOutputTranscoder(OutputTranscoder):
	'''This class implements an ANSI (VT100) terminal.
	It is a stream filter that recognizes ANSI terminal
	escape sequences and maintains the state of a screen object. '''

	def __init__ (self, *args,**kwargs):

		OutputTranscoder.__init__(self, *args, **kwargs)
		#self.screen = screen (24,80)
		self.state = FSM ('INIT',[self])

		self.state.set_default_transition (DoLog, 'INIT')
		self.state.add_transition_any ('INIT', DoEmit, 'INIT')
		self.state.add_transition ('\x1b', 'INIT', None, 'ESC')
		self.state.add_transition ('\x08', 'INIT', DoBackOne, 'INIT')
		self.state.add_transition ('\x07', 'INIT', None, 'INIT')
		self.state.add_transition_any ('ESC', DoLog, 'INIT')
		self.state.add_transition ('(', 'ESC', None, 'G0SCS')
		self.state.add_transition (')', 'ESC', None, 'G1SCS')
		self.state.add_transition_list ('AB012', 'G0SCS', None, 'INIT')
		self.state.add_transition_list ('AB012', 'G1SCS', None, 'INIT')
		self.state.add_transition ('7', 'ESC', DoCursorSave, 'INIT')
		self.state.add_transition ('8', 'ESC', DoCursorRestore, 'INIT')
		self.state.add_transition ('M', 'ESC', DoUpReverse, 'INIT')
		self.state.add_transition ('>', 'ESC', DoUpReverse, 'INIT')
		self.state.add_transition ('<', 'ESC', DoUpReverse, 'INIT')
		self.state.add_transition ('=', 'ESC', None, 'INIT') # Selects application keypad.
		self.state.add_transition ('#', 'ESC', None, 'GRAPHICS_POUND')
		self.state.add_transition_any ('GRAPHICS_POUND', None, 'INIT')
		self.state.add_transition ('[', 'ESC', None, 'ELB')
		# ELB means Escape Left Bracket. That is ^[[
		self.state.add_transition ('H', 'ELB', DoHomeOrigin, 'INIT')
		self.state.add_transition ('D', 'ELB', DoBackOne, 'INIT')
		self.state.add_transition ('B', 'ELB', DoDownOne, 'INIT')
		self.state.add_transition ('C', 'ELB', DoForwardOne, 'INIT')
		self.state.add_transition ('A', 'ELB', DoUpOne, 'INIT')
		self.state.add_transition ('J', 'ELB', DoEraseDown, 'INIT')
		self.state.add_transition ('K', 'ELB', DoEraseEndOfLine, 'INIT')
		self.state.add_transition ('r', 'ELB', DoEnableScroll, 'INIT')
		self.state.add_transition ('m', 'ELB', self.do_sgr, 'INIT')
		self.state.add_transition ('?', 'ELB', None, 'MODECRAP')
		self.state.add_transition_list (string.digits, 'ELB', DoStartNumber, 'NUMBER_1')
		self.state.add_transition_list (string.digits, 'NUMBER_1', DoBuildNumber, 'NUMBER_1')
		self.state.add_transition ('D', 'NUMBER_1', DoBack, 'INIT')
		self.state.add_transition ('B', 'NUMBER_1', DoDown, 'INIT')
		self.state.add_transition ('C', 'NUMBER_1', DoForward, 'INIT')
		self.state.add_transition ('A', 'NUMBER_1', DoUp, 'INIT')
		self.state.add_transition ('J', 'NUMBER_1', DoErase, 'INIT')
		self.state.add_transition ('K', 'NUMBER_1', DoEraseLine, 'INIT')
		self.state.add_transition ('l', 'NUMBER_1', DoMode, 'INIT')
		### It gets worse... the 'm' code can have infinite number of
		### number;number;number before it. I've never seen more than two,
		### but the specs say it's allowed. crap!
		self.state.add_transition ('m', 'NUMBER_1', self.do_sgr, 'INIT')
		### LED control. Same implementation problem as 'm' code.
		self.state.add_transition ('q', 'NUMBER_1', self.do_decsca, 'INIT')

		# \E[?47h switch to alternate screen
		# \E[?47l restores to normal screen from alternate screen.
		self.state.add_transition_list (string.digits, 'MODECRAP', DoStartNumber, 'MODECRAP_NUM')
		self.state.add_transition_list (string.digits, 'MODECRAP_NUM', DoBuildNumber, 'MODECRAP_NUM')
		self.state.add_transition ('l', 'MODECRAP_NUM', self.do_modecrap, 'INIT')
		self.state.add_transition ('h', 'MODECRAP_NUM', self.do_modecrap, 'INIT')

#RM   Reset Mode				Esc [ Ps l				   none
		self.state.add_transition (';', 'NUMBER_1', None, 'SEMICOLON')
		self.state.add_transition_any ('SEMICOLON', DoLog, 'INIT')
		self.state.add_transition_list (string.digits, 'SEMICOLON', DoStartNumber, 'NUMBER_2')
		self.state.add_transition_list (string.digits, 'NUMBER_2', DoBuildNumber, 'NUMBER_2')
		self.state.add_transition_any ('NUMBER_2', DoLog, 'INIT')
		self.state.add_transition ('H', 'NUMBER_2', DoHome, 'INIT')
		self.state.add_transition ('f', 'NUMBER_2', DoHome, 'INIT')
		self.state.add_transition ('r', 'NUMBER_2', DoScrollRegion, 'INIT')
		### It gets worse... the 'm' code can have infinite number of
		### number;number;number before it. I've never seen more than two,
		### but the specs say it's allowed. crap!
		self.state.add_transition ('m', 'NUMBER_2', self.do_sgr, 'INIT')
		### LED control. Same problem as 'm' code.
		self.state.add_transition ('q', 'NUMBER_2', self.do_decsca, 'INIT')
		self.state.add_transition (';', 'NUMBER_2', None, 'SEMICOLON_X')

		# Create a state for 'q' and 'm' which allows an infinite number of ignored numbers
		self.state.add_transition_any ('SEMICOLON_X', DoLog, 'INIT')
		self.state.add_transition_list (string.digits, 'SEMICOLON_X', DoStartNumber, 'NUMBER_X')
		self.state.add_transition_list (string.digits, 'NUMBER_X', DoBuildNumber, 'NUMBER_X')
		self.state.add_transition_any ('NUMBER_X', DoLog, 'INIT')
		self.state.add_transition ('m', 'NUMBER_X', self.do_sgr, 'INIT')
		self.state.add_transition ('q', 'NUMBER_X', self.do_decsca, 'INIT')
		self.state.add_transition (';', 'NUMBER_X', None, 'SEMICOLON_X')

	def decode(self, s):
		"""Process text, writing it to the virtual screen while handling
		ANSI escape codes.
		"""
		if isinstance(s, bytes):
			s = s.decode('UTF-8')
		self.begin_sequence()
		self.state.process_list(s)
		self.end_sequence()

	def do_sgr (self, fsm):
		'''Select Graphic Rendition, e.g. color. '''
		screen = fsm.memory[0]
		fsm.memory = [screen]

	def do_decsca (self, fsm):
		'''Select character protection attribute. '''
		screen = fsm.memory[0]
		fsm.memory = [screen]

	def do_modecrap (self, fsm):
		'''Handler for \x1b[?<number>h and \x1b[?<number>l. If anyone
		wanted to actually use these, they'd need to add more states to the
		FSM rather than just improve or override this method. '''
		screen = fsm.memory[0]
		fsm.memory = [screen]