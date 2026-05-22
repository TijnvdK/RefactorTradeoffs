#!/bin/bash

set -e

# Load environment variables from .env file if it exists
set -a
[ -f .env ] && source .env
set +a

nvidia-smi

export HF_TOKEN=""
export LD_LIBRARY_PATH=/usr/lib64:$LD_LIBRARY_PATH
export PATH=/usr/bin:$PATH

source "./.venv/bin/activate"
python "./src/runner.py"
