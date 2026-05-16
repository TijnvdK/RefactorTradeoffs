#!/usr/bin/env bash

### Configuration ###

## Directory paths ##
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP_DIR="/tmp"
OUTPUT_DIR="$SCRIPT_DIR/outputs"

if [[ ! -d "$OUTPUT_DIR" ]]; then
    echo "ERROR: Output directory '$OUTPUT_DIR' does not exist."
    exit 1
fi

## Experiment parameters ##
CPU_LOADS=(0 10 20 30 40 50 60 70 80 90 100)
HZ_VALUES=(1 10 50 100 250)  # 250 Hz is the frequency that /proc/stat is
                             # updated at the machine I am testing on.
EXPERIMENT_DURATION_SECONDS=60

### Execute the experiments in `test_cpu_util_logger.c` and also see ###
### how the frequency affects the results.                           ###

for load in "${CPU_LOADS[@]}"; do
    echo "Testing with CPU load ${load}%"

    if [ "$load" -gt 0 ]; then
        stress-ng --cpu 0 --cpu-load "$load" --timeout 0 --metrics-brief &>/dev/null &
        STRESS_PID=$!
    fi

    sleep 1  # Give stress-ng a moment to ramp up the load

    for hz in "${HZ_VALUES[@]}"; do
        echo "Testing with HZ=$hz"
        gcc -O3 -o "$TMP_DIR/latency_test_hz${hz}" \
            "$SCRIPT_DIR/test_cpu_util_logger.c" \
            -DHZ=$hz \
            -DLOG_FILE="\"$OUTPUT_DIR/cpu_util_hz${hz}_load${load}_duration${EXPERIMENT_DURATION_SECONDS}.csv\""
            -DEXPERIMENT_DURATION_SECONDS=$EXPERIMENT_DURATION_SECONDS
        "$TMP_DIR/latency_test_hz${hz}"
    done

    if [ "$load" -gt 0 ]; then
        kill "$STRESS_PID" 2>/dev/null
        wait "$STRESS_PID" 2>/dev/null
    fi
done

echo "Testing complete. Output files available in ${OUTPUT_DIR}"
