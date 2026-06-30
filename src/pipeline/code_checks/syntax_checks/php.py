from logging import getLogger
from os import unlink
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Tuple
from src.settings import settings
from subprocess import TimeoutExpired, run as subprocess_run

logger = getLogger(__name__)


def syntax_check_php(code: str) -> Tuple[bool, str]:
    """
    Checks if the provided PHP code is syntactically correct.

    Args:
        code (str): The PHP code to validate.

    Returns:
        Tuple[bool, str]: A tuple where the first element is a boolean
        indicating whether the code is syntactically correct, and the second
        element is a string containing the output of the syntax check
        (error messages if any).
    """

    stripped = code.strip()
    if not stripped:
        return (False, 'Code is empty.')

    # Append a php tag if missing to ensure the syntax check runs correctly
    if not (stripped.startswith('<?php') or stripped.startswith('<?')):
        code = '<?php\n' + code

    with NamedTemporaryFile(
        suffix='.php', mode='w', delete=False, dir=settings.job_dir
    ) as _file:
        _file.write(code)
        temp_path = _file.name

    _runner = Path(__file__).parent / 'run_php82_lint.sh'

    try:
        cmd = ['bash', str(_runner), temp_path]
        result = subprocess_run(
            cmd,
            capture_output=True,
            timeout=settings.syntax_check_timeout,
        )

        output = (result.stdout.decode() + result.stderr.decode()).strip()
        return (result.returncode == 0, output)
    except TimeoutExpired:
        logger.error(
            'PHP syntax check timed out after '
            f'{settings.syntax_check_timeout} seconds.'
        )
        return (False, 'PHP syntax check timed out.')
    finally:
        try:
            unlink(temp_path)
        except OSError as _error:
            logger.warning(
                'Failed to remove temporary lint file %s: %s',
                temp_path,
                _error,
            )
