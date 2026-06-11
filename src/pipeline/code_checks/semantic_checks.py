from logging import getLogger
from tempfile import NamedTemporaryFile
from typing import Optional, TypedDict
from src.settings import settings
from subprocess import TimeoutExpired, run as subprocess_run
from os import unlink as os_unlink

logger = getLogger(__name__)


class SemanticCheckOutput(TypedDict):
    is_valid: bool
    error_message: Optional[str]


def semantic_check_php(code: str) -> SemanticCheckOutput:
    """
    Checks if the provided PHP code is syntactically correct.

    Args:
        code (str): The PHP code to validate.

    Returns:
        SemanticCheckOutput: The result of the semantic check.
    """
    stripped = code.strip()
    if not stripped or not (
        stripped.startswith('<?php') or stripped.startswith('<?')
    ):
        return SemanticCheckOutput(
            is_valid=False,
            error_message='Code does not start with a valid PHP opening tag.',
        )

    with NamedTemporaryFile(
        suffix='.php', mode='w', delete=False, dir=settings.job_dir
    ) as f:
        f.write(code)
        tmp = f.name
    try:
        result = subprocess_run(
            [
                'apptainer',
                'exec',
                '--bind',
                f'{settings.job_dir}:{settings.job_dir}',
                '--writable-tmpfs',
                '--nv',
                '--contain',
                settings.path_to_php_cli_sif,
                'php',
                '-l',
                tmp,
            ],
            capture_output=True,
            timeout=settings.semantic_check_timeout,
        )

        if result.returncode == 0:
            return SemanticCheckOutput(is_valid=True, error_message=None)
        else:
            error_output = result.stderr.decode(
                'utf-8', errors='replace'
            ).strip()
            return SemanticCheckOutput(
                is_valid=False,
                error_message=error_output
                if error_output
                else 'PHP syntax check failed with no error message.',
            )
    except TimeoutExpired:
        logger.error('PHP syntax check timed out.')
        return SemanticCheckOutput(
            is_valid=False, error_message='PHP syntax check timed out.'
        )
    finally:
        os_unlink(tmp)
