#!/usr/bin/env python

__all__ = ['InputTranscoder']

from .utils import *

class InputTranscoder():
	def __init__(self):
		self.input_queue = Queue()

	def pop_input(self, timeout):
		try:
			i = self.input_queue.get(timeout = timeout)
		except:
			raise Empty
		else:
			return i

	def write(self, content):
		self.input_queue.put(content)

	def enter(self):
		self.input_queue.put("\n")

	def move(self, rel):	
		s = ""
		if rel > 0:
			s = ''.join(['\006' for s in range(rel)])
		elif rel < 0:
			s = ''.join(['\002' for s in range(-rel)])
		else:
			return
		self.input_queue.put(s)

	def erase(self, n=1):
		if n <= 0:
			return
		s = ''.join(['\x08' for s in range(n)])
		self.input_queue.put(s)

# [0, 1, 2, '\n'] -> 4 [a, b, c, d, '\n'] -> 5
# cursor = 0, cursor += 6 : y += 1 et x = x - (len(line) - 1) = 6 - 4 + 1 = 3

if __name__ == '__main__':
	sm = OutputTranscoder()
	sm.output_begin_sequence()
	sm.output_write("a")
	sm.output_write("z")
	sm.output_write("e")
	sm.output_write("r")
	sm.output_write("t")

	sm.output_crlf()
#	sm.output_move_backward(1)
#	sm.output_move_backward(1)
#	sm.output_lf()
#	sm.move_left(2)
#	sm.output_lf()

	sm.output_write("A")
	sm.output_write("Z")
	sm.output_write("E")
	sm.output_write("R")

#	sm.output_move_up()
#	sm.output_crlf()
	sm.output_move_backward(2)
	sm.output_erase_line()

#	sm.output_lf()
#	sm.move_left(2)
#	sm.output_move_up()
#	sm.output_write("a")
#	sm.output_write("a")
	print(sm.lines)
	sm.output_end_sequence()
	print(sm.get_last_output(timeout = 1))
	print(sm.lines)
