#!/usr/bin/env bash
set -o errexit

# Install pywin32 on Linux using pip
pip install --upgrade pip
pip install pywin32 --no-deps

# Regular install
pip install -r requirements.txt
