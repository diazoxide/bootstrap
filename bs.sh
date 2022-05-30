#!/bin/sh

if [[ $BS_FROM_DEV_PATH = "1" ]]; then
  python3 ~/PycharmProjects/bootstrap/bs.py "$@"
else
  python3 /usr/local/lib/bs/bs.py "$@"
fi