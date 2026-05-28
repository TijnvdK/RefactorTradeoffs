from pathlib import Path
from shutil import copytree, rmtree
from tempfile import mkdtemp
from typing import Tuple
from subprocess import CompletedProcess, run as subprocess_run
from uuid import uuid4
import xml.etree.ElementTree as ET

PHPUNIT_SUITES = [
    (
        'eb4',
        'XDEBUG_MODE=off ./vendor/bin/phpunit '
        + '--configuration=./tests/phpunit.xml --testsuite=eb4 '
        + '--log-junit results.xml --no-progress --no-output',
    ),
    (
        'unit',
        'XDEBUG_MODE=off ./vendor/bin/phpunit '
        + '--configuration=./tests/phpunit.xml --testsuite=unit '
        + '--log-junit results.xml --no-progress --no-output',
    ),
    (
        'functional',
        'APP_ENV=test XDEBUG_MODE=off ./vendor/bin/phpunit '
        + '--configuration=./tests/phpunit.xml --testsuite=functional '
        + '--log-junit results.xml --no-progress --no-output',
    ),
    (
        'integration',
        'XDEBUG_MODE=off ./vendor/bin/phpunit '
        + '--configuration=./tests/phpunit.xml --testsuite=integration '
        + '--log-junit results.xml --no-progress --no-output',
    ),
]


def _parse_phpunit_output(xml_output: str) -> str:
    if not xml_output.strip():
        return ''

    root = ET.fromstring(xml_output)
    results = []

    for tc in root.iter('testcase'):
        failure = tc.find('failure')
        if failure is None:
            continue

        file = tc.get('file', '')
        filename = file.rsplit('/', 1)[-1]
        line = tc.get('line', '?')
        classname = tc.get('class', '')

        location = (
            f'{filename}:{line} ({classname})'
            if classname
            else f'{filename}:{line}'
        )
        results.append(f'{location}:\n\t{(failure.text or "").strip()}')

    return '\n'.join(results)


def _compose_run(
    compose_cmd: list[str], args: list[str], cwd: str
) -> CompletedProcess:
    return subprocess_run(
        compose_cmd + args, capture_output=True, text=True, cwd=cwd
    )


def _container_exec(
    compose_cmd: list[str], cwd: str, script: str
) -> CompletedProcess:
    return _compose_run(
        compose_cmd,
        ['exec', '-T', 'engine.dev.openconext.local', 'bash', '-c', script],
        cwd,
    )


def engineblock_verifier(
    engineblock_root: Path, php_file: Path, code: str
) -> Tuple[bool, str]:
    relative_path = php_file.relative_to(engineblock_root)
    project_name = f'phpunit_{uuid4()}'
    temp_dir = Path(mkdtemp(prefix='phpunit_tmp_'))

    compose_cmd: list[str] = []
    cwd: str = ''

    try:
        repo_copy = temp_dir / 'repository_copy'
        copytree(engineblock_root, repo_copy, symlinks=True)
        (repo_copy / relative_path).write_text(code, encoding='utf-8')

        docker_dir = repo_copy / 'docker'
        cwd = str(docker_dir)
        compose_cmd = [
            'docker',
            'compose',
            '-p',
            project_name,
            '-f',
            str(docker_dir / 'docker-compose.yml'),
            '-f',
            str(docker_dir / 'docker-compose-php82.yml'),
        ]

        up = _compose_run(compose_cmd, ['up', '-d', '--build'], cwd)
        if up.returncode != 0:
            return False, f'Failed to start Docker container: {up.stderr}'

        setup_steps = [
            (
                'vendor directory preparation',
                'mkdir -p /var/www/html/vendor && '
                + 'chown -R www-data:www-data /var/www/html/vendor',
            ),
            (
                'composer install / cache:clear',
                'composer install --prefer-dist -n -o '
                + '--ignore-platform-reqs && ./bin/console cache:clear '
                + '--env=ci --no-warmup',
            ),
            (
                'doctrine schema setup',
                './bin/console doctrine:schema:drop --force --env=ci && '
                + './bin/console doctrine:schema:create --env=ci',
            ),
        ]
        for label, script in setup_steps:
            result = _container_exec(compose_cmd, cwd, script)
            if result.returncode != 0:
                return (
                    False,
                    f'{label} failed:\n{result.stderr}\n{result.stdout}',
                )

        failures = []
        for suite_name, cmd in PHPUNIT_SUITES:
            _container_exec(compose_cmd, cwd, cmd)
            parsed = _parse_phpunit_output(
                _container_exec(compose_cmd, cwd, 'cat results.xml').stdout
            )
            if parsed:
                failures.append(
                    f"Test suite '{suite_name}' failures:\n{parsed}"
                )

        if failures:
            return False, '\n'.join(failures)

        return True, ''
    finally:
        if compose_cmd:
            _compose_run(
                compose_cmd, ['down', '--volumes', '--remove-orphans'], cwd
            )
        rmtree(temp_dir, ignore_errors=True)
