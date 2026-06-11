#!/bin/bash

set -e

# Load environment variables from .env file if it exists
set -a
[ -f .env ] && source .env
set +a

nvidia-smi

# export LD_LIBRARY_PATH=/usr/lib64:$LD_LIBRARY_PATH
# export PATH=/usr/bin:$PATH

# Make sure that local scratch directory exists
export JOB_DIR=${TMPDIR}/${USER}
[[ ! -d $JOB_DIR ]] && mkdir -p $JOB_DIR
[[ ! -d $JOB_DIR/tmp ]] && mkdir -p $JOB_DIR/tmp
[[ ! -d $JOB_DIR/.cache ]] && mkdir -p $JOB_DIR/.cache

export APPTAINER_CACHEDIR=$JOB_DIR/.cache
export HF_HOME=$JOB_DIR/hf_cache

PATH_TO_REPOSITORY=$JOB_DIR/repository
cp -r /home/${USER}/repository $PATH_TO_REPOSITORY
PATH_TO_PHP_CLI_SIF=$JOB_DIR/php8-2-cli.sif
cp /home/${USER}/php8-2-cli.sif $PATH_TO_PHP_SIF
PATH_TO_OPENHANDS_SIF=$JOB_DIR/openhands.sif
cp /home/${USER}/openhands.sif $PATH_TO_OPENHANDS_SIF
PATH_TO_MARIADB_SIF=$JOB_DIR/mariadb.sif
cp /home/${USER}/mariadb.sif $PATH_TO_MARIADB_SIF
PATH_TO_PHPUNIT_SIF=$JOB_DIR/phpunit.sif
cp /home/${USER}/phpunit.sif $PATH_TO_PHPUNIT_SIF
PATH_TO_RAG_VECTOR_STORE=$JOB_DIR/rag_vector_store
cp -r /home/${USER}/rag_vector_store $PATH_TO_RAG_VECTOR_STORE

# We need to load Python3.12 and CUDA modules. On Snellius:
# module load 2025
# module load 2024
# module load Python/3.12.3-GCCcore-13.3.0
# module load CUDA/12.9.1
# Then export the following variables, or whatever their path may be:
# $ which nvcc
# > /sw/arch/RHEL9/EB_production/2025/software/CUDA/12.9.1/bin/nvcc
# export CUDA_HOME=/sw/arch/RHEL9/EB_production/2025/software/CUDA/12.9.1
# export CUDA_ROOT=$CUDA_HOME
# export CUDA_PATH=$CUDA_HOME
# export PATH=$CUDA_HOME/bin:$PATH
# export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$CUDA_HOME/targets/x86_64-linux/lib:$LD_LIBRARY_PATH

# export LD_LIBRARY_PATH=/usr/lib64:$LD_LIBRARY_PATH
# export PATH=/usr/bin:$PATH

##
# It is most like far better to let the agentic AI create refactoring opportunities itself
# And then campaign A is simply mass refactor. Have to discuss with Ana.
##

source "./.venv/bin/activate"
export PYTHONPATH="$(pwd):${PYTHONPATH}"
python "./src/runner.py" --agent refactoring --model Qwen/Qwen2.5-Coder-1.5B
# python "./src/runner.py" --agent verification --model Qwen/Qwen2.5-Coder-1.5B --iteration 0

# python -m vllm.entrypoints.openai.api_server \
#     --model devstral-2-123b \
#     --enable-prefix-caching \
#     --tensor-parallel-size N \
#     --port 8000
