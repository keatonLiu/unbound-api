#!/bin/env bash
DEBIAN_FRONTEND=noninteractive sudo apt update
DEBIAN_FRONTEND=noninteractive sudo apt install -y python3.10-venv
rm -r .venv
python3 -m venv .venv
source .venv/bin/activate && pip install -r requirements.txt
