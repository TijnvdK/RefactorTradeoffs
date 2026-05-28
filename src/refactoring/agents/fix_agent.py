from pathlib import Path
from typing import List
from json import loads as json_loads, dumps as json_dumps
from src.globals.types import CodeRecord
from src.refactoring.handlers.interface.backend_handler import BackendHandler
from src.utils import call_llm, is_valid_php_code


def fix_agent(
    llm_handler: BackendHandler,
    input_path: Path,
    output_path: Path,
    max_attempts: int = 5,
) -> None:
    code_records: List[CodeRecord] = json_loads(input_path.read_text())
    result: List[CodeRecord] = []

    for code_record in code_records:
        if not code_record['error_output']:
            result.append(code_record)
            continue  # No error to fix, skip this record

        energy_consumed = 0.0
        total_energy_consumed = code_record['total_energy_consumed']

        retries_needed = None
        output_code = ''

        for attempt in range(max_attempts):
            parsed_code, energy_consumed = call_llm(
                llm_handler,
                'Fix the following error in the following PHP code:\n\n'
                f'Error: {code_record["error_output"]}\n\n'
                f'PHP code with error:\n```{code_record["code"]}```',
            )

            total_energy_consumed += energy_consumed

            if parsed_code:
                if is_valid_php_code(parsed_code):
                    retries_needed = attempt + 1  # indexing
                    output_code = parsed_code

                    break

        result.append(
            {
                **code_record,
                'code': output_code,
                'energy_consumed_fix': energy_consumed,
                'total_energy_consumed': total_energy_consumed,
                'amount_of_fix_retries': retries_needed,
            }
        )

    output_path.write_text(json_dumps(result, indent=4))
