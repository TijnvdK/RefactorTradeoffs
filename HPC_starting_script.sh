#!/bin/bash
#SBATCH --partition=capacity
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --time=12:00:00
#SBATCH --job-name=EB_Refactor

set -euo pipefail

nvidia-smi

export EB_INSTANCE_NAME="eb_runner_${SLURM_JOB_ID:-}"

# Cleanup any running apptainers on any exit to avoid leaving dangling
# instances or processes.
cleanup() {
    apptainer instance stop "${EB_INSTANCE_NAME}" 2>/dev/null || true
}
trap cleanup EXIT

# Load environment variables from .env file if it exists
set -a
[ -f .env ] && source .env
set +a

# Create a fresh job directory
export JOB_DIR=$(realpath "${TMPDIR}/${USER}/job_${SLURM_JOB_ID}")
rm -rf $JOB_DIR

[[ ! -d $JOB_DIR ]] && mkdir -p $JOB_DIR
[[ ! -d $JOB_DIR/tmp ]] && mkdir -p $JOB_DIR/tmp
[[ ! -d $JOB_DIR/.cache ]] && mkdir -p $JOB_DIR/.cache

export APPTAINER_CACHEDIR=$JOB_DIR/.cache
export HF_HOME=$JOB_DIR/hf_cache

# Create a fresh copy of the repository in the job directory
export PATH_TO_REPOSITORY=$JOB_DIR/repository
rm -rf $PATH_TO_REPOSITORY
cp -r /home/${USER}/repository $PATH_TO_REPOSITORY
export PATH_TO_REPOSITORY_SRC=$PATH_TO_REPOSITORY/src

# Copy apptainer images to the job directory
export PATH_TO_EB_TEST_SIF=$JOB_DIR/eb_test.sif
[[ ! -f $PATH_TO_EB_TEST_SIF ]] && cp ./apptainers/eb_test.sif $PATH_TO_EB_TEST_SIF
export PATH_TO_PHP82_LINT_SIF=$JOB_DIR/php82_lint.sif
[[ ! -f $PATH_TO_PHP82_LINT_SIF ]] && cp ./apptainers/php82_lint.sif $PATH_TO_PHP82_LINT_SIF

# To make vLLM work correctly we need a set of environment variables to be set.
# We need to have both Python3.12 and CUDA modules installed/loaded.

# On Snellius this can be done as:
# ```
# module load 2025
# module load 2024
# module load Python/3.12.3-GCCcore-13.3.0
# module load CUDA/12.9.1
# ```
# Then the following variables have to be set:
# ```
# export CUDA_HOME=/usr/local/cuda-12.3
# export CUDA_ROOT=$CUDA_HOME
# export CUDA_PATH=$CUDA_HOME
# export PATH=$CUDA_HOME/bin:$PATH
# export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$CUDA_HOME/targets/x86_64-linux/lib:$LD_LIBRARY_PATH
# ```
# On UvA Hipster only the following variables have to be set, since Hipster
# already had some CUDA installation by default.
# ```
export LD_LIBRARY_PATH=/usr/lib64:${LD_LIBRARY_PATH:-}
export PATH=/usr/bin:${PATH:-}
# ```

# If you are refactoring EngineBlock, you need to setup the PHP environment.
# Uncomment the following lines to setup this environment.
# ---
export PHP_ENV_MYSQL_DATA=$JOB_DIR/.eb_test_mysql
export PHP_ENV_VAR_DIR=$JOB_DIR/.eb_var

# Initialize SQL data

[[ ! -d "${PHP_ENV_MYSQL_DATA}" ]] && mkdir -p "${PHP_ENV_MYSQL_DATA}"
# mysql_install_db runs as the current user; no --user flag needed since
# mysqld won't attempt a uid switch when already running as non-root.
apptainer exec \
    --bind "${PHP_ENV_MYSQL_DATA}:/var/lib/mysql" \
    "${PATH_TO_EB_TEST_SIF}" \
    mysql_install_db \
        --datadir=/var/lib/mysql \
        --auth-root-authentication-method=normal \
        --skip-test-db \
        --tmpdir=/var/lib/mysql \
        > /dev/null 2>&1

[[ ! -d "${PHP_ENV_VAR_DIR}/cache" ]] && mkdir -p "${PHP_ENV_VAR_DIR}/cache"
[[ ! -d "${PHP_ENV_VAR_DIR}/log" ]] && mkdir -p "${PHP_ENV_VAR_DIR}/log"

# Start the EngineBlock test environment
apptainer instance start \
    --bind "${PHP_ENV_MYSQL_DATA}:/var/lib/mysql" \
    --bind "${JOB_DIR}/tmp:/tmp" \
    --bind "${PATH_TO_REPOSITORY}/src:/var/www/html/src" \
    --bind "${PHP_ENV_VAR_DIR}:/var/www/html/var" \
    "${PATH_TO_EB_TEST_SIF}" "${EB_INSTANCE_NAME}" \
    > /dev/null 2>&1

# Waiting for MariaDB to accept connections
ELAPSED=0
until apptainer exec "instance://${EB_INSTANCE_NAME}" \
        mysqladmin --socket=/tmp/eb_test_mysql.sock ping 2>/dev/null; do
    sleep 1
    ELAPSED=$((ELAPSED + 1))
    if [ "${ELAPSED}" -ge 60 ]; then
        echo "ERROR: MariaDB did not start within 600s." >&2
        echo "--- MariaDB log ---" >&2
        apptainer exec "instance://${EB_INSTANCE_NAME}" cat /tmp/eb_mariadb.log
        exit 1
    fi
done

# Creating test databases
apptainer exec "instance://${EB_INSTANCE_NAME}" bash -c "
mysql --socket=/tmp/eb_test_mysql.sock -u root <<'SQL'
CREATE DATABASE IF NOT EXISTS eb_test
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS eb
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'eb_testrw'@'localhost' IDENTIFIED BY 'secret';
CREATE USER IF NOT EXISTS 'ebrw'@'localhost'      IDENTIFIED BY 'secret';
GRANT ALL PRIVILEGES ON eb_test.* TO 'eb_testrw'@'localhost';
GRANT ALL PRIVILEGES ON eb.*      TO 'ebrw'@'localhost';
FLUSH PRIVILEGES;
SQL
"
# ---

# Activate Python
source "./.venv/bin/activate"
export PYTHONPATH="$(pwd):${PYTHONPATH:-}"

export OPENHANDS_LOG_LEVEL=ERROR
export OPENHANDS_SUPPRESS_BANNER=1

# Everything is loaded and Ok. Start the experiment pipeline.
python -m src.pipeline.runner

# Transfer the results back to the home directory
BATCH_DIR="$HOME/job_${SLURM_JOB_ID}"
mkdir -p "$BATCH_DIR"
for run_dir in "$JOB_DIR"/run_*/; do
    cp -r "$run_dir" "$BATCH_DIR/"
done
