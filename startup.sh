#!/bin/bash

BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

cd ${BASE_DIR}

echo "Sleeping 30s to wait for proper initialization ..."
sleep 15s
python gui.py
