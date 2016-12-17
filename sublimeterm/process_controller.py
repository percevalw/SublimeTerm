#!/usr/bin/env python

from .utils import *
from .input_transcoder import *
from .ansi_output_transcoder import *

__all__ = ['ProcessController']

try:
	print("stop potentially-existing ProcessController...")
	c = ProcessController.instance.stop()
except:
	print("and there was none")
else:
	print("and there was one")

class ProcessController:
	instance = None

	def __new__(_class, input_transcoder, output_transcoder):
		if isinstance(_class.instance, _class):
			_class.instance.close()
		_class.instance = object.__new__(_class)
		return _class.instance

	def __init__(self, input_transcoder, output_transcoder):
		self.master = None
		self.slave = None
		self.process = None

		self.input_transcoder = input_transcoder
		self.output_transcoder = output_transcoder

		self.mutex = Lock()
		self.read_thread = None
		self.write_thread = None
		self.stop = False

	def start(self, command):
		""" Create the PTY """
		self.spawn(command)

		""" Loops """
		self.read_thread = Thread(target=self.keep_reading)
		self.write_thread = Thread(target=self.keep_writing)

		self.read_thread.start()
		self.write_thread.start()

	def close(self):
		self.stop = True
		try:
			os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
		except:
			print("Must already be dead")
		else:
			print("Successfully killed")

	def spawn(self, command):
		self.master, self.slave = os.openpty()
		self.process = subprocess.Popen(command,
                                        stdin = self.slave,
                                        stdout = self.slave,
                                        stderr = self.slave,
                                        preexec_fn = os.setsid)
		print("SPWAN !")

	def keep_reading(self):
		while True:
			if self.stop:
				break
			readable, writable, executable = select.select([self.master], [], [], 1)
			if readable:
				""" We read the new content """
				data = os.read(self.master, 1024)
				text = data.decode('UTF-8')
				self.output_transcoder.decode(text)
#				print("{} >> {}".format(int(time.time()), repr(text)))

	def keep_writing(self):
		while True:
			if self.stop:
				break
			readable, writable, executable = select.select([], [self.master], [], 1)
			if writable:
				try:
					text = self.input_transcoder.pop_input(timeout=1)
				except Empty:
					pass
				else:
					print("Input detected")
					data = text.encode('UTF-8')
#					data = bytes(chaine, 'iso-8859-15')
					while data:
						chars_written = os.write(self.master, data)
						data = data[chars_written:]



def main():

	input_transcoder = InputTranscoder()
	output_transcoder = ANSIOutputTranscoder()
	pty = ProcessController(input_transcoder, output_transcoder)
	pty.start()
	time.sleep(3)
	input_transcoder.write("ls\n")
	try:
		while True:
			time.sleep(10)
	except KeyboardInterrupt:
		print("\nINTERRUPTION !")
		pty.close()

if __name__ == '__main__':
	main()
