from typing import Tuple
from subprocess import TimeoutExpired, run as subprocess_run
from src.settings import settings
from uuid import uuid4
from time import sleep


def correctness_check_engineblock() -> Tuple[bool, str]:
    db_instance_name = f'mariadb_{uuid4()}'
    try:
        subprocess_run(
            [
                'apptainer',
                'instance',
                'start',
                '--env',
                'MYSQL_ROOT_PASSWORD=root,MYSQL_DATABASE=eb_test',
                settings.path_to_mariadb_sif,
                db_instance_name,
            ],
            check=True,
            capture_output=True,
        )

        # Wait a bit for the database to start up
        sleep(15)

        result = subprocess_run(
            [
                'apptainer',
                'exec',
                '--env',
                'APP_ENV=test',
                '--bind',
                f'{settings.path_to_repository}:/app',
                '--pwd',
                '/app',
                settings.path_to_phpunit_sif,
                'ci/qa/phpunit.sh',
            ],
            capture_output=True,
            text=True,
            timeout=settings.correctness_check_timeout,
        )

        return result.returncode == 0, result.stdout
    except TimeoutExpired as e:
        partial_output = e.stdout or ''
        return (
            False,
            f'Timeout after {settings.correctness_check_timeout}s.\nPartial Output:\n{partial_output}',
        )
    except Exception as e:
        return False, f'Exception occurred: {str(e)}'
    finally:
        subprocess_run(
            ['apptainer', 'instance', 'stop', db_instance_name],
            capture_output=True,
        )
