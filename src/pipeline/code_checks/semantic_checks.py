from logging import getLogger
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Tuple
from src.settings import settings
from subprocess import TimeoutExpired, run as subprocess_run

logger = getLogger(__name__)


def semantic_check_php(code: str) -> Tuple[bool, str]:
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
    if not stripped or not (
        stripped.startswith('<?php') or stripped.startswith('<?')
    ):
        return (False, 'Code does not start with a valid PHP opening tag.')

    with NamedTemporaryFile(
        suffix='.php', mode='w', delete=False, dir=settings.job_dir
    ) as _file:
        _file.write(code)

        _runner = Path(__file__).parent / 'run_php82_lint.sh'

        try:
            cmd = ['bash', str(_runner), _file.name]
            result = subprocess_run(
                cmd,
                capture_output=True,
                timeout=settings.semantic_check_timeout,
            )
            return (result.returncode == 0, result.stdout.decode())
        except TimeoutExpired:
            logger.error(
                'PHP syntax check timed out after '
                f'{settings.semantic_check_timeout} seconds.'
            )
            return (False, 'PHP syntax check timed out.')
