#!/bin/bash

set -e

# Load environment variables from .env file if it exists
set -a
[ -f .env ] && source .env
set +a

nvidia-smi

# export LD_LIBRARY_PATH=/usr/lib64:$LD_LIBRARY_PATH
# export PATH=/usr/bin:$PATH

source "./.venv/bin/activate"
export PYTHONPATH="$(pwd):${PYTHONPATH}"
python "./src/runner.py" --agent refactoring --model Qwen/Qwen2.5-Coder-1.5B
# python "./src/runner.py" --agent verification --model Qwen/Qwen2.5-Coder-1.5B --iteration 0
