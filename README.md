SublimeTerm
===========

[![Build Status](https://travis-ci.org/percevalw/SublimeTerm.svg?branch=master)](https://travis-ci.org/percevalw/SublimeTerm) [![codecov](https://codecov.io/gh/percevalw/Sublimeterm/branch/master/graph/badge.svg)](https://codecov.io/gh/percevalw/Sublimeterm)

SublimeTerm is a plugin for Sublime Text that allows you to run a shell in your editor.

VI and other readline-intensive programs (iPython, PSQL, ...) seem to run fine.
It has only been tested on OS X but it should work on Linux. Windows is not supported at the moment.

This project is still in its early stages and any contribution will be gratefully welcomed.

## Configuration

Edit the settings in `Preferences > Packages Settings > Term`.

Default command is set to "/bin/bash" in the Sublime working directory.

Example for ssh with a custom extended environment in your home directory on OS X.


```json
{
    "command": "ssh my_remote_server",
    "cwd": "/Users/username",
    "env": {
        "MY_ENV_VARIABLE": "VALUE"
    }
}
```

## Custom command

You can edit a custom command with the `command`, `env` and `cwd` settings like below (example for Keyboard shortcut)

```
{
    "keys": ["ctrl+option+@"],
    "command": "term",
    "args" : {"command": "mysql"}
}
```

## Demo time !

![](https://raw.githubusercontent.com/percevalw/Sublimeterm/master/doc/demo.gif)

## How does it work ?

This plugin acts as a standard [terminal emulator](https://en.wikipedia.org/wiki/Terminal_emulator). It is is highly multi-threaded, to avoid blocking SublimeText while waiting for the shell 'answer'. The communication with the process is made using [standard streams](https://en.wikipedia.org/wiki/Standard_streams) and Python's subprocess library.

**Input**

When you write something to the screen, the diff between the old and the new content is detected through analysis of the cursor position.

This input is translated into [ANSI Control Sequences](https://en.wikipedia.org/wiki/ANSI_escape_code) (ex: backspace becomes \x08 character, up-arrow becomes \x08[A etc) and sent to the shell (or any other program we want to communicate with) using the standard input.


**Output**

Once the program has finished processing our input, it replies using the standard output and error channels with other ANSI Control Sequences. Those are way more complicated than the input since they control color, cursor position, line-erasals etc.

Actually, they can be decoded using a [finite state machine](https://en.wikipedia.org/wiki/Finite-state_machine) and translated to actions to do in the tab. Those actions are in fact run on a virtual screen, whose content is diffed to only correct on the real screen what has really changed. We could replace the whole screen every time the program replies one of our input but this would make the user experience way slower.

## What's next ?
There is no roadmap for this project.

Colors are still missing but I have ideas on how to integrate them. Any help is welcome.

Some parts are still a bit to slow to offer a seamless terminal emulation to the user. C can be a good option to speed these up a bit.