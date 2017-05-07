#!/bin/bash

echo $(pwd)
tic term.ti
export TERM="sublimeterm"
export COLUMNS=40
tput rmam
export INPUTRC="/Users/perceval/Library/Application Support/Sublime Text 3/Packages/Sublimeterm/inputrc"
#echo -e "+-------------------------------+\n| WELCOLME TO SUBLIME SUBLIMETERM ! |\n+-------------------------------+\n"
exec "$@"
