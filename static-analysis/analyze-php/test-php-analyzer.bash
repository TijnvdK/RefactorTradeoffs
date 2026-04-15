#!/usr/bin/env bash

### See if php-analyzer script exists ###
if [[ ! -x "./php-analyzer.bash" ]]; then
    echo "ERROR: php-analyzer.bash not found in current directory."
    exit 1
fi

### Test: Check if given a PHP code directory, php-analyzer creates ###
### four XML output files in the outputs directory                  ###
if ! ./php-analyzer.bash "./example-php-code-dir"; then
    echo "ERROR: php-analyzer.bash did not execute successfully."
    exit 1
fi

EXPECTED_FILES=(
    "pdepend.xml"
    "phpcs.xml"
    "phpmd.xml"
    "phpmetrics.csv"
)
for FILE in "${EXPECTED_FILES[@]}"; do
    if [[ ! -f "./outputs/$FILE" ]]; then
        echo "ERROR: '$FILE' was not found in the outputs directory."
        exit 1
    fi
done

### END OF TESTS ###
echo "If you see this message, all tests passed successfully!"
