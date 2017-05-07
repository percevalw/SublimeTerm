#!/bin/bash

A=($@)
tic "$1/term.ti"
export TERM="sublimeterm"
export COLUMNS=40
tput rmam
export INPUTRC="$(pwd)/inputrc"

exec ${A[@]:1}
