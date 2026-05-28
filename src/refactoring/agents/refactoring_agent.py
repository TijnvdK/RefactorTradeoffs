from pathlib import Path
from typing import List
from logging import getLogger
from src.globals.types import CodeRecord, UserPrompt
from src.refactoring.handlers.interface.backend_handler import (
    BackendHandler,
)
from src.utils import call_llm, is_valid_php_code
from json import dumps as json_dumps

logger = getLogger(__name__)


def refactoring_agent(
    llm_handler: BackendHandler,
    models: List[str],
    user_prompts: List[UserPrompt],
    output_path: Path,
    max_attempts: int = 5,
) -> None:
    result: List[CodeRecord] = []
    for model in models:
        llm_handler.change_model(model)

        for user_prompt in user_prompts:
            prompt, php_file = user_prompt['prompt'], user_prompt['php_file']

            energy_consumed = 0.0
            total_energy_consumed = 0.0

            retries_needed = None
            output_code = ''

            for attempt in range(max_attempts):
                parsed_code, energy_consumed = call_llm(
                    llm_handler,
                    f'Refactor this code to be more efficient and green, with equivalent functionality.\n```{prompt}```',
                )

                total_energy_consumed += energy_consumed

                if parsed_code:
                    if is_valid_php_code(parsed_code):
                        retries_needed = attempt + 1  # indexing
                        output_code = parsed_code

                        break

            result.append(
                CodeRecord(
                    model=model,
                    php_file=php_file,
                    code=output_code,
                    energy_consumed_refactor=energy_consumed,
                    energy_consumed_fix=None,
                    total_energy_consumed=total_energy_consumed,
                    amount_of_refactoring_retries=retries_needed,
                    amount_of_fix_retries=None,
                    error_output=None,
                )
            )

    output_path.write_text(json_dumps(result, indent=4))
