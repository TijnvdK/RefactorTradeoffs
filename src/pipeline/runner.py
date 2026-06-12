from concurrent.futures import ThreadPoolExecutor, as_completed
from logging import (
    getLogger,
    basicConfig as logging_basicConfig,
    INFO as logging_INFO,
)
from pathlib import Path
from shutil import copytree
from time import time
from typing import Dict, List, TypedDict
from json import dumps as json_dumps
from src.globals.custom_exceptions import LLMCallFailed
from src.globals.types import ResultSchema, UnitResultSchema
from src.pipeline.code_checks.correctness_checks import (
    correctness_check_engineblock,
)
from src.pipeline.code_checks.semantic_checks import semantic_check_php
from src.pipeline.llm_context.tree_parser import (
    FunctionInfo,
    extract_functions,
    find_enclosing_function,
    splice_function,
)
from src.pipeline.llm_providers.openhands import run_openhands_task
from src.pipeline.llm_providers.vllm_client import History, chat
from src.pipeline.measuring_energy.cpu_rapl.cpu_energy_meter import (
    CPUEnergyMeter,
)
from src.pipeline.measuring_energy.nvidia_gpu.gpu_energy_meter import (
    GPUEnergyMeter,
)
from src.settings import settings
from json import loads as json_loads
from src.sonarqube.parse_issues import SonarQubeIssue

logger = getLogger(__name__)


class Unit(TypedDict):
    task: str
    file_path: Path
    function_info: FunctionInfo


SYSTEM_PROMPT_PASSIVE = (
    'You are a green software expert. '
    'You will be given a PHP source file and asked to refactor a specific '
    'function for energy efficiency. '
    'Return ONLY the refactored function definition, enclosed in a ```php '
    'code block. '
    "Do not change the function's name, parameters, or return type. "
    'Do not include any explanation outside the code block.'
)

SYSTEM_PROMPT_ACTIVE = (
    'You are an expert PHP developer. '
    'You will be given a PHP source file and a SonarQube issue to fix. '
    'Return ONLY the corrected function definition, enclosed in a ```php '
    'code block. '
    "Do not change the function's name, parameters, or return type. "
    'Do not include any explanation outside the code block.'
)


def _refactor(
    history: History, message: str, repo_path: Path, unit: Unit
) -> UnitResultSchema:
    original_source = unit['file_path'].read_text()

    total_llm_calls = 0
    total_tokens_in = 0
    total_tokens_out = 0
    total_tool_calls = 0

    semantic_retries = 0
    semantic_retries_total = 0
    correctness_retries_total = 0

    def _rejected_result(
        unit: Unit,
        llm_calls: int,
        tokens_in: int,
        tokens_out: int,
        semantic_retries: int,
        correctness_retries: int,
    ) -> UnitResultSchema:
        return UnitResultSchema(
            name=unit['function_info']['name'],
            file=str(unit['file_path']),
            accepted=False,
            semantic_retries=semantic_retries,
            correctness_retries=correctness_retries,
            llm_calls=llm_calls,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            tool_calls=None,
        )

    while correctness_retries_total <= settings.max_correctness_retries:
        while semantic_retries <= settings.max_semantic_retries:
            try:
                if settings.agent_type == 'agent':
                    history, refactored_code, usage = chat(history, message)
                elif settings.agent_type == 'agentic':
                    tool_calls, usage = run_openhands_task(message, repo_path)
                    total_tool_calls += tool_calls

                    refactored_code = unit['file_path'].read_text()
                else:
                    raise RuntimeError(
                        f'Unknown agent type: {settings.agent_type}'
                    )
            except LLMCallFailed as exc:
                logger.warning(
                    'LLM call failed for %s in %s: %s',
                    unit['function_info']['name'],
                    unit['file_path'],
                    exc,
                )
                return _rejected_result(
                    unit,
                    total_llm_calls,
                    total_tokens_in,
                    total_tokens_out,
                    semantic_retries_total,
                    correctness_retries_total,
                )

            total_llm_calls += 1
            total_tokens_in += usage['prompt_tokens']
            total_tokens_out += usage['completion_tokens']

            semantic_result = semantic_check_php(refactored_code)
            if semantic_result['is_valid']:
                break

            logger.debug(
                'Semantic check failed (attempt %d) for %s: %s',
                semantic_retries + 1,
                unit['function_info']['name'],
                semantic_result['error_message'],
            )
            message = (
                'The code you returned has a syntax error. Fix it and return '
                'only the corrected function in a ```php code block.\n\n'
                f'Error:\n{semantic_result["error_message"]}'
            )

            semantic_retries += 1
            semantic_retries_total += 1
        else:
            logger.warning(
                'Exhausted semantic retries for %s in %s - keeping original.',
                unit['function_info']['name'],
                unit['file_path'],
            )
            return _rejected_result(
                unit,
                total_llm_calls,
                total_tokens_in,
                total_tokens_out,
                semantic_retries_total,
                correctness_retries_total,
            )

        semantic_retries = 0  # reset for correctness loop

        if settings.agent_type == 'agent':
            file_source = unit['file_path'].read_text()
            updated_source = splice_function(
                file_source, unit['function_info'], refactored_code
            )
            unit['file_path'].write_text(updated_source)

        passed, test_output = correctness_check_engineblock()
        if passed:
            break

        logger.debug(
            'Correctness check failed (attempt %d) for %s.',
            correctness_retries_total + 1,
            unit['function_info']['name'],
        )

        # Restore original so the next attempt starts from a clean state.
        unit['file_path'].write_text(original_source)
        message = (
            'The refactored function caused test failures. Fix it and return '
            'only the corrected function in a ```php code block.\n\n'
            f'Test output:\n{test_output}'
        )

        correctness_retries_total += 1
    else:
        logger.warning(
            'Exhausted correctness retries for %s in %s - keeping original.',
            unit['function_info']['name'],
            unit['file_path'],
        )
        # Ensure original is restored
        unit['file_path'].write_text(original_source)
        return _rejected_result(
            unit,
            total_llm_calls,
            total_tokens_in,
            total_tokens_out,
            semantic_retries_total,
            correctness_retries_total,
        )

    return UnitResultSchema(
        name=unit['function_info']['name'],
        file=str(unit['file_path']),
        accepted=True,
        semantic_retries=semantic_retries_total,
        correctness_retries=correctness_retries_total,
        llm_calls=total_llm_calls,
        tokens_in=total_tokens_in,
        tokens_out=total_tokens_out,
        tool_calls=None,
    )


def _process_unit(unit: Unit, repo_path: Path) -> UnitResultSchema:
    if settings.experiment_type == 'active':
        system_prompt = SYSTEM_PROMPT_ACTIVE

        initial_message = f'{unit["task"]}'
        if settings.agent_type == 'agent':
            enclosing_code = unit['function_info']['source']
            initial_message = (
                f'Enclosing code for context:\n\n```php\n{enclosing_code}\n```'
                + initial_message
            )

    else:
        system_prompt = SYSTEM_PROMPT_PASSIVE

        initial_message = f'{unit["task"]}'
        if settings.agent_type == 'agent':
            file_source = unit['file_path'].read_text()
            initial_message = (
                f'Full source file for context:\n\n```php\n{file_source}\n```'
                + initial_message
            )

    # Shared history across ALL retries so the LLM can see every prior
    # attempt and its error.
    history: History = [{'role': 'system', 'content': system_prompt}]
    return _refactor(history, initial_message, repo_path, unit)


def _process_file_units(
    units: List[Unit], repo_path: Path
) -> List[UnitResultSchema]:
    """
    Process all units belonging to a single file sequentially.

    File-level sequencing is required because each unit may splice a new
    version of the file; processing the same file from multiple threads
    concurrently would cause line-offset corruption.
    """
    results = []
    for unit in units:
        results.append(_process_unit(unit, repo_path))
    return results


def _build_units_passive(repo_path: Path) -> List[Unit]:
    units: List[Unit] = []
    for php_file in repo_path.rglob('*.php'):
        source = php_file.read_text()
        for fn in extract_functions(source):
            units.append(
                Unit(
                    task=(
                        f'Refactor the function `{fn["name"]}` in '
                        f'`{php_file.relative_to(repo_path)}` to be more '
                        'efficient and green, while maintaining its '
                        'functionality and function signature.'
                    ),
                    file_path=php_file,
                    function_info=fn,
                )
            )
    return units


def _build_units_active(repo_path: Path) -> List[Unit]:
    issues: List[SonarQubeIssue] = json_loads(
        (
            Path(__file__).parent / 'sonarqube' / 'sonarqube_issues.json'
        ).read_text()
    )
    units: List[Unit] = []
    for issue in issues:
        # issue['file_path'] is relative to the original repo root; remap to
        # the run's copy.
        rel = Path(issue['file_path'])
        abs_path = repo_path / rel
        source = abs_path.read_text()
        fn_info = find_enclosing_function(source, issue['line'])
        units.append(
            Unit(
                task=(
                    f'Fix the SonarQube issue: {issue["message"]} '
                    f'in file `{issue["file_path"]}` at line {issue["line"]}. '
                    'Do not change the function signature of affected '
                    'functions.'
                ),
                file_path=abs_path,
                function_info=fn_info,
            )
        )
    return units


def _run(
    run_index: int,
    base_repo: Path,
    cpu_meter: CPUEnergyMeter,
    gpu_meter: GPUEnergyMeter,
):
    run_repo = Path(settings.job_dir) / f'run_{run_index}'
    copytree(base_repo, run_repo, dirs_exist_ok=False)

    if settings.experiment_type == 'passive':
        units = _build_units_passive(run_repo)
    else:
        units = _build_units_active(run_repo)

    by_file: Dict[Path, List[Unit]] = {}
    for unit in units:
        by_file.setdefault(unit['file_path'], []).append(unit)

    cpu_meter.start()
    gpu_meter.start()
    wall_start = time()

    all_unit_results: List[UnitResultSchema] = []

    max_workers = min(len(by_file), 32)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                _process_file_units, file_units, run_repo
            ): file_path
            for file_path, file_units in by_file.items()
        }
        for future in as_completed(futures):
            file_path = futures[future]
            try:
                all_unit_results.extend(future.result())
            except Exception as exc:
                logger.error(
                    'Unhandled error processing %s: %s', file_path, exc
                )

    wall_seconds = time() - wall_start
    cpu_joules = cpu_meter.stop()
    gpu_joules = gpu_meter.stop()

    accepted = [r for r in all_unit_results if r['accepted']]
    rejected = [r for r in all_unit_results if not r['accepted']]

    result = ResultSchema(
        run_index=run_index,
        experiment_type=settings.experiment_type,
        agent_type=settings.agent_type,
        model=settings.vllm_server_model_name,
        language=settings.language,
        wall_time_seconds=round(wall_seconds, 2),
        cpu_energy_joules=round(cpu_joules, 4),
        gpu_energy_joules=round(gpu_joules, 4),
        total_energy_joules=round(cpu_joules + gpu_joules, 4),
        total_llm_calls=sum(r['llm_calls'] for r in all_unit_results),
        total_tokens_in=sum(r['tokens_in'] for r in all_unit_results),
        total_tokens_out=sum(r['tokens_out'] for r in all_unit_results),
        total_processed_units=len(all_unit_results),
        total_accepted_units=len(accepted),
        total_rejected_units=len(rejected),
        acceptance_rate=round(len(accepted) / len(all_unit_results), 4)
        if all_unit_results
        else 0.0,
        per_unit_results=all_unit_results,
    )

    out_dir = (
        Path(__file__).parent.parent
        / 'results'
        / ('passive' if result['experiment_type'] == 'passive' else 'active')
        / f'run_{run_index}'
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f'run_{run_index}.json').write_text(json_dumps(result, indent=4))

    logger.info(
        'Run %d complete - accepted %d / %d units, '
        'energy %.1f J, wall time %.1f s',
        run_index,
        result['total_accepted_units'],
        result['total_processed_units'],
        result['total_energy_joules'],
        result['wall_time_seconds'],
    )


def runner():
    logging_basicConfig(
        level=logging_INFO, format='%(asctime)s - %(levelname)s - %(message)s'
    )

    base_repo = Path(settings.path_to_repository)

    cpu_meter = CPUEnergyMeter()
    gpu_meter = GPUEnergyMeter()

    for run_index in range(1, settings.run_size + 1):
        logger.info(
            'Starting run %d / %d  [%s · %s · %s]',
            run_index,
            settings.run_size,
            settings.experiment_type,
            settings.agent_type,
            settings.vllm_server_model_name,
        )

        _run(run_index, base_repo, cpu_meter, gpu_meter)


if __name__ == '__main__':
    runner()
