set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <absolute path to output directory>" >&2
    exit 2
fi

APPTAINER_RESULT=0
OUTPUT_DIR="$1"

apptainer exec --env JUNIT_DIR="/tmp/phpunit-results" "instance://${EB_INSTANCE_NAME:-}" bash <<'INNER' || APPTAINER_RESULT=$?
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
cp "${JOB_DIR}/tmp/phpunit-results/"*.xml "${OUTPUT_DIR}/"
