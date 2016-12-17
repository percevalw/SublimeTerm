#!/usr/bin/env python
# coding: utf8

import sys, os, subprocess, time, signal, select
from threading import Event, Lock, Thread
try:
	from Queue import Queue, Empty
except ImportError:
	from queue import Queue, Empty  # python 3.x

class SpecialChar:
	NEW_LINE = '\n'
	TAB = '\t'
	BEL = '\x07'
	BACKSPACE = '\x08'
	UP = '\020'
	DOWN = '\016'
	LEFT = '\002'
	RIGHT = '\006'

