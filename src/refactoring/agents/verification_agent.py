from logging import getLogger
from pathlib import Path
from typing import Callable, List, Tuple
from src.globals.types import CodeRecord
from json import loads as json_loads, dumps as json_dumps

logger = getLogger(__name__)


def verification_agent(
    input_path: Path,
    output_path: Path,
    original_code_path: Path,
    verifier: Callable[[Path, Path, str], Tuple[bool, str]],
) -> bool:
    code_records: List[CodeRecord] = json_loads(input_path.read_text())
    result: List[CodeRecord] = []

    for code_record in code_records:
        if code_record['code'] == '':
            result.append(code_record)
            continue  # Refactoring failed, no code to verify

        passed, error = verifier(
            original_code_path,
            Path(code_record['php_file']),
            code_record['code'],
        )

        result.append(
            {**code_record, 'error_output': None if passed else error}
        )

    output_path.write_text(json_dumps(result, indent=4))

    all_passed = all(record['error_output'] is None for record in result)
    return all_passed
