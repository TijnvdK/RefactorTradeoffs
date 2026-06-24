set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <absolute path to output directory> <worker index>" >&2
    exit 2
fi

APPTAINER_RESULT=0
OUTPUT_DIR="$1"
WORKER_INDEX="$2"

# Each worker has its own isolated EngineBlock environment, provisioned by
# HPC_starting_script.sh. The instance name and the host-side results
# directory are both suffixed with the worker index so concurrent correctness
# checks never share a MariaDB instance, a bound src/ tree, or JUnit output.
# EB_INSTANCE_NAME and JOB_DIR are exported by HPC_starting_script.sh; do not
# hardcode them here.
INSTANCE_NAME="${EB_INSTANCE_NAME:-}_w${WORKER_INDEX}"
RESULTS_HOST_DIR="${JOB_DIR}/tmp_w${WORKER_INDEX}/phpunit-results"

apptainer exec --env JUNIT_DIR="/tmp/phpunit-results" "instance://${INSTANCE_NAME}" bash <<'INNER' || APPTAINER_RESULT=$?
set -euo pipefail
exec > /dev/null
cd /var/www/html

RESULT=0

# Infrastructure setup
./bin/console cache:clear --env=ci --no-warmup || {
    echo "FATAL: cache:clear failed." >&2; exit 1
}

# Schema reset
./bin/console doctrine:schema:drop --force --env=ci 2>/dev/null || {
    echo "FATAL: doctrine:schema:drop failed." >&2; exit 1
}
./bin/console doctrine:schema:create --env=ci 2>/dev/null || {
    echo "FATAL: doctrine:schema:create failed." >&2; exit 1
}

# PHPUnit: eb4 (legacy)
./vendor/bin/phpunit \
    --configuration=./tests/phpunit.xml \
    --testsuite=eb4 \
    --log-junit="${JUNIT_DIR}/phpunit-eb4.xml" \
    || RESULT=$?

# PHPUnit: unit
./vendor/bin/phpunit \
    --configuration=./tests/phpunit.xml \
    --testsuite=unit \
    --log-junit="${JUNIT_DIR}/phpunit-unit.xml" \
    || RESULT=$?

# Switch Symfony environment for next test suites
./bin/console cache:clear --env=test --no-warmup || {
    echo "FATAL: cache:clear (test) failed." >&2; exit 1
}

# PHPUnit: functional
APP_ENV=test ./vendor/bin/phpunit \
    --configuration=./tests/phpunit.xml \
    --testsuite=functional \
    --log-junit="${JUNIT_DIR}/phpunit-functional.xml" \
    || RESULT=$?

# PHPUnit: integration
./vendor/bin/phpunit \
    --configuration=./tests/phpunit.xml \
    --testsuite=integration \
    --log-junit="${JUNIT_DIR}/phpunit-integration.xml" \
    || RESULT=$?

ls -la "${JUNIT_DIR}" || echo "JUNIT_DIR not visible in container"

exit $RESULT
INNER

mkdir -p "${OUTPUT_DIR}"
cp "${RESULTS_HOST_DIR}/"*.xml "${OUTPUT_DIR}/"
