set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <absolute path to output directory>" >&2
    exit 2
fi

OUTPUT_DIR="$1"



apptainer exec "instance://eb_runner" bash <<'INNER'
set -euo pipefail
cd /var/www/html

RESULT=0

# Infrastructure setup
./bin/console cache:clear --env=ci --no-warmup || {
    echo "FATAL: cache:clear failed." >&2; exit 1
}

# Schema reset
./bin/console doctrine:schema:drop --force --env=ci || {
    echo "FATAL: doctrine:schema:drop failed." >&2; exit 1
}
./bin/console doctrine:schema:create --env=ci || {
    echo "FATAL: doctrine:schema:create failed." >&2; exit 1
}

# PHPUnit: eb4 (legacy)
./vendor/bin/phpunit \
    --configuration=./tests/phpunit.xml \
    --testsuite=eb4 \
    --log-junit="${OUTPUT_DIR}/phpunit-eb4.xml" \
    || RESULT=$?

# PHPUnit: unit
./vendor/bin/phpunit \
    --configuration=./tests/phpunit.xml \
    --testsuite=unit \
    --log-junit="${OUTPUT_DIR}/phpunit-unit.xml" \
    || RESULT=$?

# Switch Symfony environment for next test suites
./bin/console cache:clear --env=test --no-warmup || {
    echo "FATAL: cache:clear (test) failed." >&2; exit 1
}

# PHPUnit: functional
APP_ENV=test ./vendor/bin/phpunit \
    --configuration=./tests/phpunit.xml \
    --testsuite=functional \
    --log-junit="${OUTPUT_DIR}/phpunit-functional.xml" \
    || RESULT=$?

# PHPUnit: integration
./vendor/bin/phpunit \
    --configuration=./tests/phpunit.xml \
    --testsuite=integration \
    --log-junit="${OUTPUT_DIR}/phpunit-integration.xml" \
    || RESULT=$?

exit $RESULT
INNER
