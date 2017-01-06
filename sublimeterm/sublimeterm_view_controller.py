#!/usr/bin/env python

"""
##################
For a user input
|a b|c d|e f g h| BEFORE USER CHANGE -> cd surounded by view_mod_begin, view_mod_end
    |   \__
    |      \
|a b|X X X X|e f g h| AFTER USER CHANGE -> XXXX surounded by view_mod_begin, view_mod_end + view_mod_delta

##################
For process output
|a|b c|d e f g h| BEFORE PROC CHANGE -> c surounded by proc_mod_begin, proc_mod_end - proc_mod_delta
  |   \
  |    \
|a|O O O|d e f g h| AFTER PROC CHANGE -> OOO (proc_mod_content) surounded by proc_mod_begin, proc_mod_end

##########
Correction
|a:b|X X X X|e f g h| -> bXXXX surounded by corr_view_begin and corr_view_end
  |        /
  |       /
|a|O O O|d:e f g h| -> 000d surounded by corr_proc_begin and corr_proc_end

if (proc_mod_begin >= view_mod_begin and proc_mod_begin <= view_mod_end) or \
   (proc_mod_end >= view_mod_begin and proc_mod_end <= view_mod_end):
    corr_view_begin = min(view_mod_begin, proc_mod_begin)
    corr_view_end = max(view_mod_end, proc_mod_end)

"""

import logging
import time
from threading import Event, Lock, Thread

import sublime
import sublime_api

try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty  # python 3.x

logger = logging.getLogger()
from .input_transcoder import *
from .ansi_output_transcoder import *
from .process_controller import *

__all__ = ['SublimetermViewController']

logger = logging.getLogger()

def debug(*args):
    logger.debug(" ".join(map(str, args)))

try:
    # debug("stop potentially-existing SublimetermViewController...")
    c = SublimetermViewController.instance.close()
except:
    # debug("and there was none")
    pass
else:
    # debug("and there was one")
    pass


class SublimetermViewController():
    instance = None

    def __del__(self):
        debug("SublimetermViewController should have been deleted !")

    def __new__(cls, input_transcoder, output_transcoder):
        if isinstance(cls.instance, cls):
            cls.instance.close()

        cls.instance = object.__new__(cls)
        return cls.instance

    def __init__(self, input_transcoder, output_transcoder):
        self.master = None

        self.view_mod_begin = 0

        self.input_transcoder = input_transcoder
        self.output_transcoder = output_transcoder

        self.cache_cursor_dep = False
        self.dont_notify_for_selection = False
        self.no_input_event = Event()
        self.no_input_event.set()

        self.last_sel = (0, 0)
        self.content_size = 0
        self.view_mod_begin = 0
        self.view_mod_end = 0
        self.view_mod_delta = 0
        self.is_content_dirty = False
        self.is_cursor_dirty = True

        self.last_width = 0
        self.last_height = 0
        self.last_size = 0

        self.has_unprocessed_inputs = False
        self.has_just_changed_view = False
        self.console = None
        self.input_queue = Queue()
        self.lock = Lock()

        self.stop = False

    def start(self):
        """ Loops """
        self.open_view()
        self.erase(0)
        self.place_cursor(0)

        self.editing_thread = Thread(target=self.keep_editing)
        self.listening_thread = Thread(target=self.keep_listening)

        self.editing_thread.start()
        self.listening_thread.start()

    def close(self):
        self.stop = True
        SublimetermViewController.instance = None

    """
    Called when the view content is modified
    To avoid that some content is written by the client
    during the execution, and therefore that the readed
    content is compromised, we clear an event that
    is being waited by the output writer
    """

    def on_modified(self):
        debug("SIZES", self.console.size(), self.last_size, self.dont_notify_for_selection,
                  self.has_just_changed_view)

        size = self.console.size()

        self.dont_notify_for_selection = True
        if self.has_just_changed_view:
            self.last_size = size
            self.has_just_changed_view = False
            return

        self.no_input_event.clear()
        # time.sleep(0.5)
        current_sel = self.console.sel()

        debug("ACC SIZES", self.console.size(), self.last_size)
        delta = size - self.last_size
        last_position = self.last_sel
        if delta > 0:
            new_position = current_sel[-1].b
        else:
            new_position = current_sel[0].a

        self.compute_change_interval(last_position, new_position, delta)
        debug("HAS UNPROCESS INPUTS", self.has_unprocessed_inputs)
        if delta > 0:
            """
            If the cursor moved forward, then some content has been added
            """
            content = self.console.substr(sublime.Region(last_position, last_position + delta))
            debug("ADDED CONTENT BETWEEN", last_position, last_position + delta, " : ", repr(content))
            debug("PROCESS CONTENT SIZE", self.output_transcoder.content_size)
            """ This part has been tranfered to the process controller """
            #            if new_position <= self.output_transcoder.max_cursor() + 1:
            #                self.compute_change_interval(last_position, new_position)
            self.input_queue.put((0, content))

        elif delta < 0:
            """
            Else, some content has been erased
            """
            debug("ERASED CONTENT BETWEEN", last_position + delta, last_position)
            self.input_queue.put((1, -delta))

        self.last_size = size
        self.last_sel = self.console.sel()[0].a
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
        #        if self.has_just_changed_view:
        #            self.has_just_changed_view = False
        #            return

        if self.dont_notify_for_selection:
            self.dont_notify_for_selection = False
            return

        self.no_input_event.clear()

        last_position = self.last_sel
        self.last_sel = self.console.sel()[0].a

        debug("CURRENT SEL, [{}, {}]".format(self.console.sel()[0].a, self.console.sel()[0].b))

        if last_position != self.last_sel:
            #            self.compute_change_interval(last_position, self.last_sel)
            rel = self.last_sel - last_position
            debug("CHANGED CURSOR", rel)
            self.input_queue.put((2, rel))

        self.no_input_event.set()

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

        last_position = self.last_sel
        self.last_sel = self.console.sel()[0].a

        #        self.compute_change_interval(last_position, self.last_sel)

        self.input_queue.put((0, char))

        self.no_input_event.set()

    def compute_change_interval(self, last_position, new_position, delta):
        debug("COMPUTE CHANGE", last_position, new_position, "DELTA", delta)
        if not self.is_content_dirty:
            self.view_mod_begin = min(last_position, new_position)
            self.view_mod_end = max(last_position + delta, new_position)
            self.view_mod_delta = delta
            debug("FIRST INTERVAL BETWEEN", self.view_mod_begin, self.view_mod_end, "DELTA", self.view_mod_delta)
            self.is_content_dirty = True
            return
        # ie new_position < last_position

        self.view_mod_begin = min(self.view_mod_begin, new_position, last_position)
        self.view_mod_end = max(self.view_mod_end + delta, last_position + delta)
        self.view_mod_delta += delta
        debug("AFTER INTERVAL, BETWEEN", self.view_mod_begin, self.view_mod_end, "DELTA", self.view_mod_delta)

    """
    Called when the process has some content to log
    We avoid to disturb any input detection process
    by waiting for a "no-input" event
    """

    def write_output(self, begin, end, string):
        if self.stop:
            return
        """
        We wait that a potential user input has been processed
        """
        pos = self.console.sel()[0].a
        self.no_input_event.wait()
        self.has_just_changed_view = True
        will_make_selection = pos == begin == end
        #        debug("POS0", self.console.sel()[0].a)
        sublime_api.view_run_command(self.console.view_id, "sublimeterm_editor", {
            "action": 2,
            "begin": begin,
            "end": end,
            "string": string,
            "cursor": pos if will_make_selection else -1
        })
        #        pos = self.console.sel()[0].a
        debug("NEW SEL IN CONSOLE", ', '.join(["[{}, {}]".format(sel.a, sel.b) for sel in self.console.sel()]))
        debug("NEW CONSOLE SIZE", self.console.size())

    #        if will_make_selection:
    #            #debug("DIFFERENT SEL", self.console.sel()[0].a, self.console.sel()[0].b)
    #            self.console.sel().add(sublime.Region(pos))
    #            debug("AFTER SEL CORR", ', '.join(["[{}, {}]".format(sel.a, sel.b) for sel in self.console.sel()]))
    #            self.has_just_changed_view = True
    #            sublime_api.view_run_command(self.console.view_id, "sublimeterm_editor", {})
    #        debug("POS", self.console.sel()[0].a)
    #        """
    #        """
    #        debug("POS2", self.console.sel()[0].a)

    #        self.last_sel = self.console.sel()[0].a

    #         We infer the future position of the cursor and sync it
    #         in the class to avoid no-new content detection
    #        added = pos+len(string)-size
    #        if added > 0 and self.last_sel >= pos:
    #            self.last_sel += added

    """
    Erase everything after pos
    Useful when the typed key ends to be not displayed
    so we must hide it
    Ex : do you want ... ? y/n -> y -> y is not displayed
    """

    def erase(self, begin, end=-1):
        if self.stop:
            return

        self.no_input_event.wait()

        if end == -1:
            end = self.console.size()
        if end <= begin:
            return
        self.has_just_changed_view = True

        sublime_api.view_run_command(self.console.view_id, "sublimeterm_editor", {
            "action": 1,
            "begin": begin,
            "end": end,
        })

    """
    Puts the cursor as the desired position in the view
    The wanted position should NOT be inferior the view size
    """

    def place_cursor(self, pos):
        if self.stop:
            return

        self.no_input_event.wait()

        self.last_sel = self.console.sel()[0].a
        debug(str(("SCREEN SIZE", self.console.size(), "WANTED", pos, "CURRENT", self.last_sel)))
        if self.console.size() < pos:

            self.console.sel().clear()
            self.console.sel().add(sublime.Region(self.last_sel))
            self.has_just_changed_view = True

            sublime_api.view_run_command(self.console.view_id, "sublimeterm_editor", {})
            debug("THERE MUST BE AN ERROR")

            time.sleep(2)

            self.cancel_view_mod()
            """
            debug("INSERT TO FILL", "SIZE", self.console.size(), "POS", pos, "CURRENT", self.console.sel()[0].a)
            num = pos - self.console.size()
            sublime_api.view_run_command(self.console.view_id, "sublimeterm_editor", {
                "action":0,
                "begin":self.console.size(),
                "string":''.join([' ' for i in range(num)])
            })
            self.console.sel().clear()
            self.console.sel().add(sublime.Region(pos))
#            self.console.show_at_center(pos)
            """
        elif self.last_sel != pos:
            self.console.sel().clear()
            self.console.sel().add(sublime.Region(pos))
            self.has_just_changed_view = True
            sublime_api.view_run_command(self.console.view_id, "sublimeterm_editor", {"begin": pos})
        self.last_sel = pos
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

    def open_view(self, output_panel=False):
        window = sublime.active_window()
        if not output_panel:
            self.console = window.open_file("sublimeterm.output")
            self.console.set_scratch(True)
            #            self.console.set_name("Sublimeterm console")
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
        if len(self.console.sel()) > 0:
            self.last_sel = self.console.sel()[0].a
        else:
            self.console.sel().add(sublime.Region(0))
            self.last_sel = 0

    """
    Puts the cursor at the 3/4 of the viewport if it is further
    """

    def show_cursor(self):
        (w, h) = self.console.viewport_extent()
        (x, y) = self.console.text_to_layout(self.console.sel()[0].a)  # viewport_position()
        (cx, cy) = self.console.viewport_position()
        return
        next_cy = y - h * 0.75
        if cy < next_cy and y > h * 0.75:
            pass
        else:
            return
        self.console.set_viewport_position((cx, next_cy))

    def get_view_size(self):
        (w, h) = self.console.viewport_extent()
        if w == self.last_width and h == self.last_height:
            return None
        self.last_width = w
        self.last_height = h
        debug("SIZE CHANGE", w / self.console.em_width(), h / self.console.line_height())
        return (int(w / self.console.em_width()) - 3, int(h / self.console.line_height()) - 1, int(w), int(h))

    def keep_listening(self):
        cached_cursor_dep = None
        (action, content) = (-1, "")
        while True:
            if self.stop:
                break
            try:
                if self.has_unprocessed_inputs:
                    (action, content) = self.input_queue.get(block=False)
                else:
                    (action, content) = self.input_queue.get(timeout=1)
            except Empty:
                self.lock.acquire()
                size = self.get_view_size()
                if size:
                    self.input_transcoder.set_size(*size)
                    self.output_transcoder.set_size(*size)
                elif self.has_unprocessed_inputs:
                    debug("INPUT QUEUE EMPTY")
                self.has_unprocessed_inputs = False
                self.lock.release()
            else:
                self.lock.acquire()
                #                time.sleep(0.3)

                if action == 2 and self.cache_cursor_dep is True:
                    if cached_cursor_dep is None:
                        cached_cursor_dep = content
                    else:
                        cached_cursor_dep += content
                else:
                    self.has_unprocessed_inputs = True
                    if cached_cursor_dep is not None and self.cache_cursor_dep is True:
                        self.input_transcoder.move(cached_cursor_dep)
                        cached_cursor_dep = None
                    if action == 0:
                        self.input_transcoder.write(content)
                    elif action == 1:
                        self.input_transcoder.erase(content)
                    elif action == 2 and self.cache_cursor_dep is False:
                        self.input_transcoder.move(content)
                self.lock.release()
        debug("EDITING ENDED")

    def compute_correction(self, proc_mod_begin, proc_mod_end, proc_mod_delta, content=None):
        """ If the process inserted some characters, ie did not replace those under the cursor at
            there position, then the view should "insert" them, ie put them in a region smaller than
            the size of the content, thus '- proc_mod_delta' """
        if 0 < proc_mod_delta < self.view_mod_begin > 0:
            pass
        elif self.view_mod_begin < proc_mod_delta < 0:
            pass
        if self.is_content_dirty:
            """ Where will we change the content in the view ? """
            corr_view_begin = min(proc_mod_begin, self.view_mod_begin)
            corr_view_end = max(self.view_mod_end, proc_mod_end - proc_mod_delta + self.view_mod_delta)

            """ What are we going to put there """
            corr_proc_begin = corr_view_begin
            corr_proc_end = corr_view_end - self.view_mod_delta + proc_mod_delta

            debug("VIEW MOD [", self.view_mod_begin, ",", self.view_mod_end, "]", "PROC MOD [", proc_mod_begin, ",",
                      proc_mod_end, "]", "PROC DELTA", proc_mod_delta, "VIEW DELTA", self.view_mod_delta,
                      "CORR VIEW : [", corr_proc_begin, ",", corr_view_end, "], ", "CORR PROC : [", corr_proc_begin,
                      ",", corr_proc_end, "]")
        else:
            """ Where will we change the content in the view ? """
            corr_view_begin = min(proc_mod_begin, self.console.size())
            corr_view_end = proc_mod_end - proc_mod_delta

            """ What are we going to put there """
            corr_proc_begin = corr_view_begin
            corr_proc_end = corr_view_end + proc_mod_delta

            debug("NOT DIRTY", "PROC MOD [", proc_mod_begin, ",", proc_mod_end, "]", "PROC DELTA", proc_mod_delta,
                      "CORR VIEW : [", corr_view_begin, ",", corr_view_end, "], ", "CORR PROC : [", corr_proc_begin,
                      ",", corr_proc_end, "]")

        """ If we need more content that what has been given by the get_last_output function """
        if content is None or corr_view_begin < proc_mod_begin or proc_mod_end < corr_proc_end:
            content = self.output_transcoder.get_between(corr_proc_begin, corr_proc_end)

        self.write_output(corr_view_begin, corr_view_end, content)
        debug("OUTPUT WRITTEN BEWTEEN {} and {}: {} (len {})".format(corr_view_begin, corr_view_end, content if len(content) <= 10 else content[:4] + '...' + content[-4:], len(content)))

        self.is_content_dirty = False

    def cancel_view_mod(self):
        self.compute_correction(self.view_mod_begin, self.view_mod_begin, 0)

    def keep_editing(self):
        position = 0
        has_unprocessed_outputs = True
        while True:
            if self.stop:
                break
            try:
                # in those particuliar circumstances, we do not want to wait
                if has_unprocessed_outputs or self.has_unprocessed_inputs:
                    (content, proc_mod_begin, position, proc_mod_end, proc_mod_delta,
                     self.content_size) = self.output_transcoder.pop_output()
                else:
                    (content, proc_mod_begin, position, proc_mod_end, proc_mod_delta,
                     self.content_size) = self.output_transcoder.pop_output(timeout=0.1)
                debug(
                    "TXT: {}, MIN:{}, POS:{}, MAX:{}, INSERT_NB:{}, TOTAL:{}".format(repr(content), proc_mod_begin,
                                                                                     position, proc_mod_end,
                                                                                     proc_mod_delta, self.content_size))
            except Empty:
                self.lock.acquire()
                #                debug("GOT HERE BECAUSE", self.has_unprocessed_inputs, has_unprocessed_outputs)
                if self.is_content_dirty and not self.has_unprocessed_inputs:
                    debug("CONTENT DIRTY AND END OF INPUTS", has_unprocessed_outputs)
                    self.cancel_view_mod()
                    self.is_cursor_dirty = True

                if self.is_cursor_dirty:
                    debug("END OF OUTPUT AND CURSOR DIRTY")
                    self.place_cursor(position)
                    self.is_cursor_dirty = False
                    self.show_cursor()
                if self.console.size() > self.content_size:
                    self.erase(self.content_size)

                if not self.has_unprocessed_inputs:
                    has_unprocessed_outputs = False
                self.lock.release()
                pass
            else:
                self.lock.acquire()
                has_unprocessed_outputs = True

                self.compute_correction(proc_mod_begin, proc_mod_end, proc_mod_delta, content)

                """
                We replace the view content between those limits
                """

                #                if will_clean_to_min_change:
                #                    debug("CONTENT DIRTY, ERASE TO FIRST CHANGE")
                #                    self.erase(replace_view_end, self.view_mod_begin)
                #                if will_clean_to_end:
                #                    debug("CONTENT NOT DIRTY, ERASE TO END")
                #                    self.erase(self.content_size)
                #                    self.is_content_dirty = False


                """
                If the changes between self.view_mod_begin, self.view_mod_end have
                been overwritten
                """

                """
                If there are no further user-interactions to treat
                we update the cursor position
                """
                #                if not self.has_unprocessed_inputs:
                #                    debug("NO OTHER INPUTS TO TREAT")
                #                    self.place_cursor(position)
                #                    self.show_cursor()
                #                else:
                self.is_cursor_dirty = True
                self.lock.release()
        debug("LISTENING ENDED")


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
        debug("\nINTERRUPTION !")
        pty.close()
        view_controller.close()


if __name__ == '__main__':
    main()
