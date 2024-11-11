#!/usr/bin/env bash
# This script should be run from the root of the project, NOT the scripts directory

source .venv/bin/activate

pip install -r requirements.txt
python3 -m venv --upgrade-deps .venv/

