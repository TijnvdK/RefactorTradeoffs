#!/bin/bash

# Deliberately not setting `set -e` here. The script is called from Python, and
# we want to capture the exit code and output of the PHP linter, even if it
# fails. If we set `set -e`, the script would exit immediately on a non-zero
# exit code, and we wouldn't be able to capture the output.
set -uo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <file.php>" >&2
    exit 2
fi

FILE="$1"

# Each concurrent invocation gets its own cache dir so parallel `apptainer run`
# calls of the same image do not race on a shared APPTAINER_CACHEDIR.
LINT_CACHE="${JOB_DIR}/.lint_cache_$$"
mkdir -p "${LINT_CACHE}"
raw=$(APPTAINER_CACHEDIR="${LINT_CACHE}" \
    apptainer run --bind "$JOB_DIR:$JOB_DIR" "$PATH_TO_PHP82_LINT_SIF" "$FILE" 2>&1)
status=$?
rm -rf "${LINT_CACHE}"

if [[ ${status} -eq 0 ]]; then
    exit 0
fi

# Non-zero exit. Try to extract a clean PHP parse/fatal error message.
filtered=$(echo "$raw" \
    | grep -E "^(PHP Parse error|PHP Fatal error)" \
    | sed -E 's/^PHP (Parse|Fatal) error:[[:space:]]*//' \
    | sed -E 's/ in (.+) on line ([0-9]+)$//' \
    | while IFS= read -r msg; do
        loc=$(echo "$raw" | grep -Eo 'in .+ on line [0-9]+' | head -1)
        lineno=$(echo "$loc" | grep -Eo '[0-9]+$')
        echo "ERROR | line $lineno | $msg"
    done)

if [[ -n "$filtered" ]]; then
    echo "$filtered"
elif [[ -n "$raw" ]]; then
    # Not a recognised PHP error (e.g. an apptainer runtime failure).
    echo "$raw"
else
    # Non-zero exit with no output at all.
    echo "php -l runner failed (exit ${status}) with no output for ${FILE}"
fi

exit 1
