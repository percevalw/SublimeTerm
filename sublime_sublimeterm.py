import sublime, sublime_plugin, sublime_api
import sys, imp, os
import logging

from . import sublimeterm

imp.reload(sublimeterm)

"""
############################
Sublimeterm Command Class
Main command class, called 
at the opening of the plugin
############################
"""
class SublimetermCommand(sublime_plugin.WindowCommand):
    def run(self, make_new=False, key = None, **kwargs):
        print("command")
        c = sublimeterm.SublimetermViewController.instance

        if c and key:
            if key == "enter":
                c.write_special_character(sublimeterm.SpecialChar.NEW_LINE)
            if key == "up":
                c.write_special_character(sublimeterm.SpecialChar.UP)
            if key == "down":
                c.write_special_character(sublimeterm.SpecialChar.DOWN)
            if key == "tab":
                c.write_special_character(sublimeterm.SpecialChar.TAB)
            if key == "escape":
                c.write_special_character(sublimeterm.SpecialChar.ESCAPE)
            return

        imp.reload(sublimeterm)

        print("\n############ BEGINNING SUBLIME SUBLIMETERM ############")
        print("NEW", make_new)

        # RELOADING SETTINGS
        self.settings = sublime.load_settings("Sublimeterm.sublime-settings")
        print("VERSION", sys.version_info)
        print("CWD", os.getcwd())
#        if c and not make_new:
#            c.open_view()
#            c.clean_console()
#        else:

        it = sublimeterm.InputTranscoder()
        ot = sublimeterm.ANSIOutputTranscoder()
        view_controller = sublimeterm.SublimetermViewController(it, ot)
        process_controller = sublimeterm.ProcessController(it, ot)

        cmd = os.path.join(sublime.packages_path(), "Sublimeterm/sublimeterm.sh")
        print(cmd)

        view_controller.start()
        process_controller.start(cmd)

#        print(dir(sublime_api))

        #self.place_cursor(0)
#        def cb():
#            self.write_output(3, "TEST")
#        sublime.set_timeout(cb, 2000)

#aaaaa aaaaa aaaa dddd ddd ezzzz eee eee 
"""
##########################
SublimetermEditorCommand Class
Used to modify the view
##########################
"""
class SublimetermEditorCommand(sublime_plugin.TextCommand):
    def run(self, edit, action = 0, begin = 0, end = 0, string = "", cursor = -1):
        if cursor >= 0:
            self.view.sel().clear()
        if action == 0:
            #print("EDITOR INSERT", repr(string), "AT", begin)
            self.view.insert(edit, begin, string)
        elif action == 1 and begin < end:
            #print("EDITOR ERASE", begin, end)
            self.view.erase(edit, sublime.Region(begin, end))
        elif action == 2:
            #print("EDITOR REPLACE", repr(string), "AT", begin, end, "INSTEAD OF", repr(self.view.substr(sublime.Region(begin, end))))
            self.view.replace(edit, sublime.Region(begin, end), string)
        if cursor >= 0:
            self.view.sel().add(sublime.Region(cursor))
            self.view.insert(edit, 0, "")


class SublimetermListener(sublime_plugin.EventListener):
    def on_text_command(self, window, name, args):
        pass

    def on_query_context(self, view, key, operator, operand, match_all):
        c = sublimeterm.SublimetermViewController.instance
        if key == "sublimeterm_open_console" or (key == "sublimeterm_event" and c and view == c.console):
            return True

    def on_selection_modified(self, view):
        c = sublimeterm.SublimetermViewController.instance
        if c and view == c.console:
            c.on_selection_modified()

    def on_modified(self, view):
        c = sublimeterm.SublimetermViewController.instance
        if c and view == c.console:
            c.on_modified()

    def on_close(self, view):
        c = sublimeterm.SublimetermViewController.instance
        p = sublimeterm.ProcessController.instance
        if c.console is not None and view == c.console:
            print("--------- DESACTIVATED ---------")
            if p:
                p.close()
            if c:
                c.close()
            #show_console()
"""
TODO : Change this class methods and attributes to static
Put most of the SublimetermCommand methods in this one
"""
