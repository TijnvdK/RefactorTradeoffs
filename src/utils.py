from logging import getLogger
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Generator, Tuple
from src.globals.custom_exceptions import LMCallFailed
from src.refactoring.handlers.interface.backend_handler import BackendHandler
from re import compile as re_compile, DOTALL as re_DOTALL
from os import unlink as os_unlink
from subprocess import run as subprocess_run

logger = getLogger(__name__)


def estimate_token_count(text: str) -> int:
    from tiktoken import get_encoding

    encoding = get_encoding('cl100k_base')
    return len(encoding.encode(text))


def file_to_str_gen(
    dir_path: Path, extension: str
) -> Generator[Tuple[Path, str], None, None]:
    """
    Generates strings from files with a specific extension in a directory.
    Function returns a generator such that not all files are read into memory
    at once.

    Args:
        dir_path (Path): The path to the directory containing the files.
        extension (str): The file extension to filter by (e.g., '.php').

    Yields:
        Tuple[Path, str]: A tuple containing the relative file path from
            dir_path and the file content as a string.
    """

    for file in dir_path.glob(f'**/*{extension}'):
        with open(file, 'r', encoding='utf-8') as f:
            yield (file.relative_to(dir_path), f.read())


_CODE_FENCED = re_compile(
    r'(`{3,})(?:[^\n`]+\n(?!\1)|\n?)(.*?)(?:\n?\1|$)', re_DOTALL
)
_CODE_TRAILING_FENCH = re_compile(r'^(.*?)\n?```', re_DOTALL)


def parse_refactored_code(raw_output: str) -> str:
    r"""
    Parses the raw output from the LLM to extract the refactored code snippet.
    The function considers the following cases (the function extracts {code}):
    1. \`\`\`{code}\`\`\` w and w/o {language} tag
    2. \`\`\`\\n{code}\\n\`\`\` w and w/o {language} tag
    3. \`\`\`\\n{code}\`\`\` w and w/o {language} tag
    4. \`\`\`{code}\\n\`\`\` w and w/o {language} tag
    5. \`\`\`\\n{code} w and w/o {language} tag and newline
    6. {code}\\n\`\`\` w and w/o newline
    The function tries to parse on order of priority. Where case 1 has the
    highest priority and case 6 the lowest.

    Limitations:
    - The function always retrieves the first code snippet if multiple code
        snippets are present in the raw output.
    - In case 5, it will retrieve everything after the opening code fence.
    - The correctness of the function is not guaranteed with nested code fences.
    - The function returns the code exactly as is, without any additional
        formatting or cleanup.

    Args:
        raw_output (str): String with a supposed code snippet,
            possibly with code fences.

    Returns:
        str: The extracted code snippet without code fences, or the original
            string if no code fences are found.
    """

    match = _CODE_FENCED.search(raw_output)
    if match and not (
        match.group(2) == ''
        and match.start() > 0
        and match.end() == len(raw_output)
    ):
        return match.group(2)

    match = _CODE_TRAILING_FENCH.search(raw_output)
    if match:
        return match.group(1)

    return raw_output


def call_llm(llm_handler: BackendHandler, prompt: str) -> Tuple[str, float]:
    """
    Single LLM call wrapped in GPU energy measurement.

    Args:
        llm_handler (BackendHandler): The handler to interact with the LLM.
        prompt (str): The prompt to send to the LLM.

    Returns:
        Tuple[str, float]: A tuple containing the parsed output from the LLM and
            the energy consumed in joules.
    """
    try:
        from src.energy_measurement.nvidia_gpu.nvidia_smi_wrapper import (
            GPUEnergyMeter,
        )
    except ModuleNotFoundError as exc:
        raise RuntimeError('GPUEnergyMeter requires GPU dependencies.') from exc

    meter = GPUEnergyMeter()

    meter.start()

    raw_output = ''
    try:
        raw_output = llm_handler.send_message(prompt)
    except LMCallFailed as e:
        logger.error(f'LMCallFailed: {e}')

    energy = meter.stop()

    parsed_output = parse_refactored_code(raw_output)
    return (parsed_output, energy)


def is_valid_php_code(code: str) -> bool:
    """
    Checks if the provided PHP code is syntactically correct.

    Args:
        code (str): The PHP code to validate.

    Returns:
        bool: True if the code is valid, False otherwise.
    """
    with NamedTemporaryFile(suffix='.php', mode='w', delete=False) as f:
        f.write(code)
        tmp = f.name
    try:
        result = subprocess_run(
            ['php', '-l', tmp], capture_output=True, timeout=10
        )
        return result.returncode == 0
    finally:
        os_unlink(tmp)
