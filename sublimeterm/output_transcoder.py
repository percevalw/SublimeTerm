#!/usr/bin/env python

__all__ = ['OutputTranscoder']

from .utils import *

def log(*args):
	s = ' '.join(map(str, args))
	print('%s' % s)

class OutputTranscoder():
	def __init__(self):

		self.x = 0
		self.y = 0
		self.cursor = 0
		self.min_seq_cursor = 0
		self.max_seq_cursor = 0
		self.dirty_cursor = False
		self.last_clean_x = 0
		self.last_clean_y = 0

		self.content = []
		self.lines = [0]

		self.changed_event = Event()
		self.changed_content = ""
		self.flushed = True
		self.io_mutex = Lock()
		self.is_processing = Lock()

	def close(self):
		self.loop = False
		self.join()

	def convert_xy(self, offset):
		o = offset
		for (y, line) in enumerate(self.lines):
			if o < line:
				return (o, y)
			else:
				o -= line
		return (o, len(self.lines))

	def convert_offset(self, x, y):
		offset = x
		if y >= len(lines):
			raise Exception
		for line in self.lines[:y]:
			offset += line
		return offset

	def begin_sequence(self):
		with self.io_mutex:
			self.is_processing.acquire()
			if self.flushed:
				self.min_seq_cursor = self.cursor
				self.max_seq_cursor = self.cursor

	def end_sequence(self):
		self.clean_cursor()
		with self.io_mutex:
			self.changed_content = ''.join(self.content[self.min_seq_cursor:self.max_seq_cursor])
			log("## {}".format(self.changed_content))
			self.flushed = False
			self.changed_event.set()
			self.is_processing.release()

	def pop_output(self, timeout):
		if not self.changed_event.wait(timeout = timeout):
			raise Empty
		else:
			with self.io_mutex:
				self.changed_event.clear()
				self.flushed = True
				return (self.changed_content, self.min_seq_cursor, self.cursor, self.max_seq_cursor, self.x, self.y)

	def get_between(self, begin, end):
		return ''.join(self.content[begin:end])

	def write_char(self, ch):
		log("\n<< PUT", repr(ch))
		log("BEFORE -> X, Y :", self.x, self.y, "CURSOR :", self.cursor, "LINES :", self.lines)
		self.clean_cursor()
		if self.x >= self.lines[self.y] - 1:
			self.content.insert(self.cursor, ch)
			self.lines[self.y] += 1
			self.x += 1
			self.cursor += 1
			self.max_seq_cursor = max(self.cursor, self.max_seq_cursor)
			self.last_clean_x = self.x
		else:
			self.content[self.cursor] = ch
			self.x += 1
			self.cursor += 1
			self.max_seq_cursor = max(self.cursor, self.max_seq_cursor)
			self.last_clean_x = self.x
		log("AFTER  -> X, Y :", self.x, self.y, "CURSOR :", self.cursor, "LINES :", self.lines)

	def write(self, ch):
		log("\n<< WRITE", ch)
		if ch == '\n':
			self.crlf()
		elif ch == '\r':
			self.cr()
		else:
			self.write_char(ch)

	def lf(self):
		log("\n<< LF")
		log("BEFORE -> X, Y :", self.x, self.y, "CURSOR :", self.cursor, "LINES :", self.lines)
		self.move_down()
		self.clean_cursor()
		log("AFTER  -> X, Y :", self.x, self.y, "CURSOR :", self.cursor, "LINES :", self.lines)

	def cr(self):
		log("\n<< CR")
		log("BEFORE -> X, Y :", self.x, self.y, "CURSOR :", self.cursor, "LINES :", self.lines)		
		self.move_to(x=0)
		self.clean_cursor()
		log("AFTER  -> X, Y :", self.x, self.y, "CURSOR :", self.cursor, "LINES :", self.lines)

	def crlf(self):
		log("\n<< CRLF")
		log("BEFORE -> X, Y :", self.x, self.y, "CURSOR :", self.cursor, "LINES :", self.lines)
		self.move_down()
		self.move_to(x=0)
		self.clean_cursor()
		log("AFTER  -> X, Y :", self.x, self.y, "CURSOR :", self.cursor, "LINES :", self.lines)

	def move_to(self, x = -1, y = -1):
		self.dirty_cursor = True
		if x>=0: self.x = x
		if y>=0: self.y = y

	def move_backward(self, n = 1):
		self.dirty_cursor = True
		self.x -= n

	def move_forward(self, n = 1):
		self.dirty_cursor = True
		self.x += n

	def move_up(self, n = 1):
		self.dirty_cursor = True
		self.y -= n

	def move_down(self, n = 1):
		self.dirty_cursor = True
		self.y += n

	def clean_cursor(self):		
		if not self.dirty_cursor:
			return
		dirty_x = self.x
		dirty_y = self.y
		self.x = self.last_clean_x
		self.y = self.last_clean_y
		self.dirty_cursor = False


		if dirty_x < 0:
			dirty_x = 0
		if dirty_y < 0:
			dirty_y = 0

		while self.y < dirty_y:
			log("DIRTY Y > Y ")
			self.cursor += self.lines[self.y]
			self.y += 1
			if self.y >= len(self.lines):
				self.cursor += 1 # We add a '\n' at the end of the previous line
				self.lines[-1] += 1
				self.content.append('\n')
				self.lines.append(0)

		while self.y > dirty_y:
			log("DIRTY Y < Y ")
			self.y -= 1
			self.cursor -= self.lines[self.y]

		if self.x < dirty_x and dirty_x < self.lines[self.y]:
			self.cursor += dirty_x - self.x

		elif dirty_x >= self.lines[self.y]:
			missing = dirty_x - self.lines[self.y]
			insert_pos = self.cursor + self.lines[self.y] - self.x
			if self.y < len(self.lines) - 1:
				missing += 1
				insert_pos -= 1

			log("MISSING", missing, "DIRTY X", dirty_x, "X", self.x)

			self.content[insert_pos:insert_pos] = [" "] * missing

			self.cursor += dirty_x - self.x
			self.max_seq_cursor += missing
			self.lines[self.y] += missing

		elif dirty_x < self.x:
			log("DIRTY X < X ")
			self.cursor += dirty_x - self.x

		self.x = dirty_x

		self.last_clean_x = self.x
		self.last_clean_y = self.y

		self.min_seq_cursor = min(self.cursor, self.min_seq_cursor)
		self.max_seq_cursor = max(self.cursor, self.max_seq_cursor)

		log("CLEAN CURSOR", self.cursor, self.x, self.y)

	def erase_end_of_line(self):
		self.clean_cursor()

		self.max_seq_cursor -= self.lines[self.y] - self.x - 1
		to = self.cursor + (self.lines[self.y] - self.x)
		if self.y < len(self.lines)-1:
			self.max_seq_cursor -= self.lines[self.y] - self.x - 1
			self.lines[self.y] = self.x + 1
			to -= 1
		else:
			self.max_seq_cursor -= self.lines[self.y] - self.x
			self.lines[self.y] = self.x
		del self.content[self.cursor:to]

	def erase_start_of_line(self):
		self.clean_cursor()

		self.max_seq_cursor -= self.x
		fr = self.cursor - self.x
		self.lines[self.y] -= self.x
		self.x = 0
		self.min_seq_cursor = min(self.cursor, self.min_seq_cursor)
		del self.content[fr:self.cursor]
		self.cursor = fr

	def erase_line(self):
		self.clean_cursor()

		fr = self.cursor - self.x
		to = self.cursor + (self.lines[self.y] - self.x)

		self.x = 0
		self.cursor = fr
		self.min_seq_cursor = min(self.cursor, self.min_seq_cursor)
		if self.y < len(self.lines)-1:
			self.max_seq_cursor -= self.lines[self.y] - 1
			self.lines[self.y] = 1
			to -= 1
		else:
			self.max_seq_cursor -= self.lines[self.y]
			self.lines[self.y] = 0
		del self.content[fr:to]

	def erase_screen(self):
		self.cursor = 0
		self.y = 0
		self.x = 0
		self.last_clean_x = 0
		self.last_clean_y = 0
		self.dirty_cursor = False
		self.min_seq_cursor = 0
		self.max_seq_cursor = len(self.content) - 1

		self.content = []
		self.lines = [0]

# [0, 1, 2, '\n'] -> 4 [a, b, c, d, '\n'] -> 5
# cursor = 0, cursor += 6 : y += 1 et x = x - (len(line) - 1) = 6 - 4 + 1 = 3

if __name__ == '__main__':
	sm = OutputTranscoder()
	sm.begin_sequence()
	sm.write("a")
	sm.write("z")
	sm.write("e")
	sm.write("r")
	sm.write("t")

	sm.crlf()
#	sm.move_backward(1)
#	sm.move_backward(1)
#	sm.lf()
#	sm.move_left(2)
#	sm.lf()

	sm.write("A")
	sm.write("Z")
	sm.write("E")
	sm.write("R")

#	sm.move_up()
#	sm.crlf()
	sm.move_backward(2)
	sm.erase_line()

#	sm.lf()
#	sm.move_left(2)
#	sm.move_up()
#	sm.write("a")
#	sm.write("a")
	log(sm.lines)
	sm.end_sequence()
	log(sm.get_last_output(timeout = 1))
	log(sm.lines)
