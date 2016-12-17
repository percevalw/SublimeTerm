#!/usr/bin/env python

import sublime, sublime_plugin, sublime_api
from .utils import *
from .input_transcoder import *
from .ansi_output_transcoder import *
from .process_controller import *

__all__ = ['SublimetermViewController']

try:
	print("stop potentially-existing SublimetermViewController...")
	c = SublimetermViewController.instance.stop()
except:
	print("and there was none")
else:
	print("and there was one")


class SublimetermViewController():
	instance = None

	def __del__(self):
		print("SublimetermViewController should have been deleted !")

	def __new__(_class, input_transcoder, output_transcoder):
		if isinstance(_class.instance, _class):
			_class.instance.close()

		_class.instance = object.__new__(_class)
		return _class.instance

	def __init__(self, input_transcoder, output_transcoder):
		self.master = None

		self.min_dirty_position = 0

		self.input_transcoder = input_transcoder
		self.output_transcoder = output_transcoder

		self.dont_notify_for_selection = False
		self.no_input_event = Event()
		self.no_input_event.set()
		self.known_position = 0
		self.min_dirty_position = 0
		self.dirty_after = True
		self.has_unprocessed_inputs = False
		self.has_just_changed_view = False
		self.console = None
		self.input_queue = Queue()
		self.lock = Lock()

		self.stop = False

	def start(self):
		""" Loops """
		self.open_view()

		self.editing_thread = Thread(target=self.keep_editing)
		self.listening_thread = Thread(target=self.keep_listening)

		self.editing_thread.start()
		self.listening_thread.start()

	def close(self):
		self.stop = True

	"""
	Called when the view content is modified
	To avoid that some content is written by the client 
	during the execution, and therefore that the readed 
	content is compromised, we clear an event that
	is being waited by the output writer
	"""
	def on_modified(self):
		print("MODIFIED,", self.has_just_changed_view)
		self.dont_notify_for_selection = True
		if self.has_just_changed_view:
			self.has_just_changed_view = False
			return

		self.no_input_event.clear()
		#time.sleep(0.5)
		last_position = self.known_position
		self.known_position = self.console.sel()[0].a

		
		if last_position < self.known_position:
			"""
			If the cursor moved forward, then some content has been added
			"""
			content = self.console.substr(sublime.Region(last_position, self.known_position))
			self.has_unprocessed_inputs = True
			self.input_queue.put((0, content))
			
		elif last_position > self.known_position:
			"""
			Else, some content has been erased
			"""

			"""
			The new minimum dirty position has to be updated
			"""
			if self.min_dirty_position < 0:
				self.min_dirty_position = self.known_position
			else:
				self.min_dirty_position = min(self.known_position, self.min_dirty_position)
			self.has_unprocessed_inputs = True
			self.input_queue.put((1, last_position - self.known_position))

		self.no_input_event.set()

	"""
	Called when the view cursor is moved
	To avoid that some content is written by the client 
	during the execution, we clear an event that
	is being waited by the output writer
	"""
	def on_selection_modified(self):
		"""
		TODO : There is something todo here, regarding
		whether it is important or not to prevent a notification
		when the client changes the cursor
		"""
#		if self.has_just_changed_view:
#			self.has_just_changed_view = False
#			return

		if self.dont_notify_for_selection:
			self.dont_notify_for_selection = False
			return

		self.no_input_event.clear()

		last_position = self.known_position
		self.known_position = self.console.sel()[0].a

		if last_position != self.known_position:

			if last_position > self.known_position:
				if self.min_dirty_position < 0:
					self.min_dirty_position = self.known_position
				else:
					self.min_dirty_position = min(self.known_position, self.min_dirty_position)

			self.input_queue.put((2, self.known_position))

		self.no_input_event.set()

		print("OK !")


	"""
	Update the known position of the cursor
	It is important to do it thread safely
	to avoid the content-modification-detector
	to invent/forget bits of strings

	TODO : find what may disturb other methods such as write_output
	when this one is fired
	"""
	def write_special_character(self, char):
		self.no_input_event.clear()

		self.known_position = self.console.sel()[0].a

		self.has_unprocessed_inputs = True
		self.input_queue.put((0, char))

		self.no_input_event.set()
		
	"""
	Called when the process has some content to print
	We avoid to disturb any input detection process
	by waiting for a "no-input" event
	"""
	def write_output(self, pos, string):
		"""
		We wait that a potential user input has been processed
		"""
		self.no_input_event.wait()

		self.has_just_changed_view = True
		sublime_api.view_run_command(self.console.view_id, "sublimeterm_editor", {
			"action":2,
			"begin":pos,
			"end":pos+len(string),
			"string":string
		})
		self.known_position = self.console.sel()[0].a

		self.show_cursor()

# 		We infer the future position of the cursor and sync it
# 		in the class to avoid no-new content detection
#		added = pos+len(string)-size
#		if added > 0 and self.known_position >= pos:
#			self.known_position += added

	"""
	Erase everything after pos
	Useful when the typed key ends to be not displayed
	so we must hide it
	Ex : do you want ... ? y/n -> y -> y is not displayed
	"""
	def erase_to_end(self, pos):
		self.no_input_event.wait()

		s = self.console.size()
		if s <= pos:
			return
		self.has_just_changed_view = True
		sublime_api.view_run_command(self.console.view_id, "sublimeterm_editor", {
			"action":1,
			"begin":pos,
			"end":s,
		})

	"""
	Puts the cursor as the desired position in the view
	The wanted position should NOT be inferior the view size
	"""
	def place_cursor(self, pos):
		self.no_input_event.wait()

		self.known_position = self.console.sel()[0].a
		if self.console.size() < pos:
			print("THERE MUST BE AN ERROR, WANTED CURSOR", pos, "; CONSOLE SIZE", self.console.size())
			"""
			print("INSERT TO FILL", "SIZE", self.console.size(), "POS", pos, "CURRENT", self.console.sel()[0].a)
			num = pos - self.console.size()
			sublime_api.view_run_command(self.console.view_id, "sublimeterm_editor", {
				"action":0,
				"begin":self.console.size(),
				"string":''.join([' ' for i in range(num)])
			})
			self.console.sel().clear()
			self.console.sel().add(sublime.Region(pos))
#			self.console.show_at_center(pos)
			"""
		elif self.known_position != pos:
			self.console.sel().clear()
			self.console.sel().add(sublime.Region(pos))
			self.has_just_changed_view = True
			sublime_api.view_run_command(self.console.view_id, "sublimeterm_editor", {
				"string":"",
				"begin":pos
			})
		self.known_position = pos
		self.show_cursor()

	"""
	###########################
	Sublime View helper methods
	###########################
	"""

	"""
	Open the view we're going to work in and
	lock it (read_only) until everything is set
	"""
	def open_view(self, output_panel = False):
		window = sublime.active_window()
		if not output_panel:
			self.console = window.open_file("/Users/perceval/Programmes/Python/SQLSublimeterm/sublimeterm.output")
			self.console.set_scratch(True)
#			self.console.set_name("Sublimeterm console")
			self.console.set_read_only(False)
			window.focus_view(self.console)
		else:
			self.console = window.find_output_panel("sublimeterm")
			if not self.console:
				self.console = window.create_output_panel("sublimeterm")
			window.run_command("show_panel", {"panel": "output.sublimeterm"})
			self.console.set_read_only(False)
			window.focus_view(self.console)
		self.console.set_viewport_position((0, 0))
		self.console.settings().set("auto_match_enabled", False)
		self.known_position = self.console.sel()[0].a

	"""
	Puts the cursor at the 3/4 of the viewport if it is further
	"""
	def show_cursor(self):
		(w, h) = self.console.viewport_extent()
		(x, y) = self.console.text_to_layout(self.console.sel()[0].a)#viewport_position()
		(cx, cy) = self.console.viewport_position()
		next_cy = y-h*0.75
		if cy < next_cy and y > h*0.75:
			pass
		else:
			return
		self.console.set_viewport_position((cx, next_cy))

	def keep_listening(self):
		moved_console_position = None
		while True:
			if self.stop:
				break
			try:
				(action, content) = self.input_queue.get(timeout=0.01)
			except Empty:
				self.lock.acquire()
				self.has_unprocessed_inputs = False
				self.lock.release()
			else:
				self.lock.acquire()
#				time.sleep(0.3)

				print(action, content)

				if action == 2:
					moved_console_position = content
				else:
				# INDENT
					if moved_console_position != None:
						self.input_transcoder.move(moved_console_position)
						moved_console_position = None
					if action == 0:
						self.input_transcoder.write(content)
					elif action == 1:
						self.input_transcoder.erase(content)
					self.dirty_after = True # TODO : remove this line
				# END INDENT
				self.lock.release()

	def keep_editing(self):
		min_position = 0
		max_position = 0
		position = 0
		while True:
			if self.stop:
				break
			try:
				(content, min_position, position, max_position, x, y) = self.output_transcoder.pop_output(timeout = 0.01)
				print("TXT: {}, MIN:{}, POS:{}, MAX:{}".format(repr(content), min_position, position, max_position))
			except Empty:
				self.lock.acquire()
				if self.dirty_after:# and not self.has_unprocessed_inputs:
					self.dirty_after = False

					self.erase_to_end(max_position)
					self.place_cursor(position)
					print("WAS DIRTY : CLEANED IT, NEW POS", position)
				self.lock.release()
				pass
			else:
				self.lock.acquire()

				replace_begin = min(min_position, self.console.size())
				if self.min_dirty_position > 0:
					replace_begin = min(replace_begin, self.min_dirty_position)

				"""
				This part is to avoid the erasal of prompt or other
				immuable parts of the term
				"""
				if replace_begin < min_position:
					print("REPLACING MORE BECAUSE DIRTY, FROM", replace_begin)
					content = self.output_transcoder.get_between(replace_begin, max_position)

				self.write_output(replace_begin, content)

				self.min_dirty_position = -1
				self.dirty_after = True

				if self.dirty_after and not self.has_unprocessed_inputs:
					self.dirty_after = False

					self.erase_to_end(max_position)
					self.place_cursor(position)
					print("WAS DIRTY : CLEANED IT, NEW POS", position)
 
				self.lock.release()


def main():

	input_transcoder = InputTranscoder()
	output_transcoder = ANSIOutputTranscoder()

	pty = ProcessController(input_transcoder, output_transcoder)
	view_controller = SublimetermViewController(input_transcoder, output_transcoder)
	
	pty.start()
	view_controller.start()
	
	time.sleep(3)
	input_transcoder.write("ls\n")
	try:
		while True:
			time.sleep(10)
	except KeyboardInterrupt:
		print("\nINTERRUPTION !")
		pty.close()
		view_controller.close()


if __name__ == '__main__':
	main()
