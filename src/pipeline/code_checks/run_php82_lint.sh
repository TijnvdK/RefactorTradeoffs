set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <file.php>" >&2
    exit 2
fi

FILE="$1"

raw=$(apptainer run --bind "$JOB_DIR:$JOB_DIR" "$PATH_TO_PHP82_LINT_SIF" "$FILE" 2>&1) && exit 0

filtered=$(echo "$raw" \
    | grep -E "^(PHP Parse error|PHP Fatal error)" \
    | sed -E 's/^PHP (Parse|Fatal) error:[[:space:]]*//' \
    | sed -E 's/ in (.+) on line ([0-9]+)$//' \
    | while IFS= read -r msg; do
        loc=$(echo "$raw" | grep -Eo 'in .+ on line [0-9]+' | head -1)
        lineno=$(echo "$loc" | grep -Eo '[0-9]+$')
        echo "ERROR | line $lineno | $msg"
    done)

if [[ -z "$filtered" ]]; then
    echo "$raw"
else
    echo "$filtered"
fi

exit 1
