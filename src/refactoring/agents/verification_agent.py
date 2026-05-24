from pathlib import Path
from typing import List, Tuple

from src.globals.types import CodeRecord
from json import loads as json_loads, dumps as json_dumps


def run_phpunit(php_file: Path, code: str) -> Tuple[bool, str]:
    return (True, '')  # Placeholder for actual implementation


def verification_agent(input_path: Path, output_path: Path) -> bool:
    code_records: List[CodeRecord] = json_loads(input_path.read_text())
    result: List[CodeRecord] = []

    for code_record in code_records:
        if code_record['code'] == '':
            continue  # Refactoring failed, no code to verify

        passed, error = run_phpunit(
            Path(code_record['php_file']), code_record['code']
        )

        result.append(
            {**code_record, 'error_output': None if passed else error}
        )

    output_path.write_text(json_dumps(result, indent=4))

    all_passed = all(record['error_output'] is None for record in result)
    return all_passed
