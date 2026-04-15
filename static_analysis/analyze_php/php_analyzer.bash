#!/usr/bin/env bash

### Configuration ###

## Directory paths ##
SCRIPT_DIR="$PWD"
PHARS_DIR="$SCRIPT_DIR/phars"
OUTPUT_DIR="$SCRIPT_DIR/outputs/raw_output"

if [[ ! -d "$PHARS_DIR" ]]; then
    echo "ERROR: PHARs directory '$PHARS_DIR' does not exist."
    exit 1
fi

if [[ ! -d "$OUTPUT_DIR" ]]; then
    echo "ERROR: Output directory '$OUTPUT_DIR' does not exist."
    exit 1
fi

## Container configuration ##
CONTAINER_NAME="php-analyzer-$$"
IMAGE_NAME="php-analyzer-image-$$"

### Analyzer ###

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <path-to-php-code-directory>"
    exit 1
fi

PHP_CODE_DIR="$1"
if [[ ! -d "$PHP_CODE_DIR" ]]; then
    echo "ERROR: Directory '$PHP_CODE_DIR' does not exist."
    exit 1
fi

echo "LOG: Config and state validated, proceeding with analysis"

echo "LOG: Building Docker image"
docker build --quiet -t "$IMAGE_NAME" - <<'EOF'

FROM php:8.4-cli
RUN apt-get update -qq && \
    apt-get install -y -qq libxml2-dev && \
    docker-php-ext-install xml && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

EOF

echo "LOG: Starting container and running analysis in Docker container"
docker run --name "$CONTAINER_NAME" \
    -v "$PHP_CODE_DIR":/php-code:ro \
    -v "$PHARS_DIR":/phars:ro \
    -v "$OUTPUT_DIR":/outputs \
    "$IMAGE_NAME" bash -c '
        php /phars/pdepend.phar --summary-xml=/outputs/pdepend.xml \
            /php-code
        php /phars/phpcs.phar --report=xml --report-file=/outputs/phpcs.xml \
            /php-code
        php /phars/phpmd.phar /php-code xml \
            cleancode,codesize,controversial,design,naming,unusedcode \
            --reportfile=/outputs/phpmd.xml
        php /phars/phpmetrics.phar --report-csv=/outputs/phpmetrics.csv \
            /php-code
    ' > /dev/null

echo "Analysis complete. Output files available in ${OUTPUT_DIR}"

echo "LOG: Removing created resources"
docker rm -f "$CONTAINER_NAME" > /dev/null
docker rmi -f "$IMAGE_NAME" > /dev/null
