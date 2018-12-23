#!/bin/sh

# Runs the given command with the nearest .env up the filesystem hierarchy.

DOTENV=''
CURDIR="$PWD"
while [ "$CURDIR" != "/" ]; do
    if [ -f "$CURDIR/.env" ]; then
        DOTENV="$CURDIR/.env"
        break
    fi
    echo "$CURDIR"
    CURDIR="$(readlink -m ..)"
done

[ -n "$DOTENV" ] && . "$DOTENV"
$@
