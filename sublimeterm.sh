#!/bin/bash
# file: sql_sublimeterm

export LANG="fr_FR.UTF-8"
#export TERM="xterm-256color"
export TERM="sublimeterm"
#export COLUMNS=65535
export COLUMNS=40
tput rmam
#stty columns 30
export PS1="\h:\W \u\$ "
#export PS1="$ "
export INPUTRC="/Users/perceval/Library/Application Support/Sublime Text 3/Packages/Sublimeterm/inputrc"
#/Applications/Postgres.app/Contents/Versions/latest/bin/psql bde -c 'select * from "Associations";'
#/Applications/Postgres.app/Contents/Versions/9.5/bin/psql bde
#echo -e "+-------------------------------+\n| WELCOLME TO SUBLIME SUBLIMETERM ! |\n+-------------------------------+\n"
/bin/bash
#echo "PHRASE A ECRIRE \n DEUIXEME PHRASE"
#--output=/Users/perceval/fichier.out