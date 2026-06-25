from concurrent.futures import ThreadPoolExecutor, as_completed
from logging import (
    getLogger,
    basicConfig as logging_basicConfig,
    INFO as logging_INFO,
)
from pathlib import Path
from queue import SimpleQueue
from shutil import copyfile, copytree
from threading import Lock
from time import time
from typing import Dict, List, TypedDict
from json import dumps as json_dumps
from src.globals.custom_exceptions import LLMCallFailed
from src.globals.types import ResultSchema, UnitResultSchema
from src.pipeline.code_checks.correctness_checks import (
    correctness_check_eb,
)
from src.pipeline.code_checks.semantic_checks import semantic_check_php
from src.pipeline.llm_context.tree_parser import (
    FunctionInfo,
    extract_functions,
    find_enclosing_function,
    relocate_function,
    splice_function,
)
from src.pipeline.llm_providers.openhands import OpenHandsSession
from src.pipeline.llm_providers.vllm_client import History, chat
from src.pipeline.llm_providers.vllm_server import (
    start_vllm_server,
    stop_vllm_server,
)
from src.pipeline.measuring_energy.cpu_rapl.cpu_energy_meter import (
    CPUEnergyMeter,
)
from src.pipeline.measuring_energy.nvidia_gpu.gpu_energy_meter import (
    GPUEnergyMeter,
)
from src.pipeline.worker_context import (
    claim_worker_index,
    get_worker_repo,
    provision_worker_repos,
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


_processed_unit_count = 0
_processed_unit_count_lock = Lock()


def _refactor(
    history: History, message: str, repo_path: Path, unit: Unit
) -> UnitResultSchema:
    """
    Perform a singular refactoring operation. This involves performing the
    LLM refactoring, checking its semantic correctness, and checking its
    functionality correctness.


    Args:
        history (History): The starting history of the refactoring operation.
        message (str): The initial refactoring task.
        repo_path (Path): The path to the repository containing the source
            files.
        unit (Unit): The unit to be refactored.

    Raises:
        RuntimeError: If the agent type is unknown.

    Returns:
        UnitResultSchema: The result of the refactoring operation.
    """

    original_source = unit['file_path'].read_text()

    total_llm_calls = 0
    total_tokens_in = 0
    total_tokens_out = 0
    total_tool_calls = 0

    semantic_retries = 0
    semantic_retries_total = 0
    correctness_retries_total = 0

    # For the agent type, create one persistent session so that retry
    # feedback messages are sent as follow-up turns in the same conversation,
    # giving the agent full context of prior attempts and errors.
    openhands_session = (
        OpenHandsSession(repo_path) if settings.agent_type == 'agent' else None
    )

    def _rejected_result() -> UnitResultSchema:
        # Write back original source to ensure a clean state for the next
        # attempt or the next unit.
        unit['file_path'].write_text(original_source)

        return UnitResultSchema(
            name=unit['function_info']['name'],
            file=str(unit['file_path']),
            accepted=False,
            equal_to_original=True,
            semantic_retries=semantic_retries_total,
            correctness_retries=correctness_retries_total,
            llm_calls=total_llm_calls,
            tokens_in=total_tokens_in,
            tokens_out=total_tokens_out,
            tool_calls=total_tool_calls,
        )

    while correctness_retries_total <= settings.max_correctness_retries:
        while semantic_retries <= settings.max_semantic_retries:
            try:
                if settings.agent_type == 'standard':
                    history, refactored_code, usage = chat(history, message)
                elif settings.agent_type == 'agent':
                    assert openhands_session is not None
                    tool_calls_before = openhands_session.tool_call_count
                    usage = openhands_session.send(message)
                    total_tool_calls += (
                        openhands_session.tool_call_count - tool_calls_before
                    )
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
                return _rejected_result()

            total_llm_calls += 1
            total_tokens_in += usage['prompt_tokens']
            total_tokens_out += usage['completion_tokens']

            if settings.agent_type == 'standard':
                file_source = unit['file_path'].read_text()
                current_info = relocate_function(
                    file_source, unit['function_info']
                )
                if current_info is None:
                    logger.warning(
                        'Could not relocate %s in %s - keeping original.',
                        unit['function_info']['name'],
                        unit['file_path'],
                    )
                    return _rejected_result()
                code_to_check = splice_function(
                    file_source, current_info, refactored_code
                )
            else:
                code_to_check = refactored_code

            if code_to_check == original_source:
                logger.info(
                    'No changes detected for %s in %s, No checks needed.',
                    unit['function_info']['name'],
                    unit['file_path'],
                )
                return UnitResultSchema(
                    name=unit['function_info']['name'],
                    file=str(unit['file_path']),
                    accepted=True,
                    equal_to_original=True,
                    semantic_retries=semantic_retries_total,
                    correctness_retries=correctness_retries_total,
                    llm_calls=total_llm_calls,
                    tokens_in=total_tokens_in,
                    tokens_out=total_tokens_out,
                    tool_calls=total_tool_calls,
                )

            passed, check_output = semantic_check_php(code_to_check)
            if passed:
                logger.info(
                    'Semantic check passed for %s in %s.',
                    unit['function_info']['name'],
                    unit['file_path'],
                )
                checked_source = code_to_check
                break

            logger.info(
                'Semantic check failed (attempt %d) for %s: %s',
                semantic_retries + 1,
                unit['function_info']['name'],
                check_output,
            )
            if settings.agent_type == 'standard':
                message = (
                    'The code you returned has a syntax error. Fix it and '
                    'return only the corrected function in a ```php code '
                    f'block.\n\nError:\n{check_output}'
                )
            else:
                message = (
                    'The file you wrote has a syntax error:\n\nError:\n'
                    f'{check_output}\n\nFix it.'
                )

            semantic_retries += 1
            semantic_retries_total += 1
        else:
            logger.warning(
                'Exhausted semantic retries for %s in %s - keeping original.',
                unit['function_info']['name'],
                unit['file_path'],
            )
            return _rejected_result()

        semantic_retries = 0  # reset for correctness loop

        if settings.agent_type == 'standard':
            unit['file_path'].write_text(checked_source)

        passed, test_output = correctness_check_eb()
        if passed:
            logger.info(
                'Correctness check passed for %s in %s.',
                unit['function_info']['name'],
                unit['file_path'],
            )
            break

        logger.info(
            'Correctness check failed (attempt %d) for %s.',
            correctness_retries_total + 1,
            unit['function_info']['name'],
        )

        logger.info(f'test output: {test_output}')

        # Restore original so the next attempt starts from a clean state.
        if settings.agent_type == 'standard':
            unit['file_path'].write_text(original_source)
            message = (
                'The refactored function caused test failures. Fix it and '
                'return only the corrected function in a ```php code '
                f'block.\n\nTest output:\n{test_output}'
            )
        else:
            message = (
                'The tests failed after your changes:\n\nTest output:\n'
                f'{test_output}\n\nFix it.'
            )

        correctness_retries_total += 1
    else:
        logger.warning(
            'Exhausted correctness retries for %s in %s - keeping original.',
            unit['function_info']['name'],
            unit['file_path'],
        )
        return _rejected_result()

    return UnitResultSchema(
        name=unit['function_info']['name'],
        file=str(unit['file_path']),
        accepted=True,
        equal_to_original=False,
        semantic_retries=semantic_retries_total,
        correctness_retries=correctness_retries_total,
        llm_calls=total_llm_calls,
        tokens_in=total_tokens_in,
        tokens_out=total_tokens_out,
        tool_calls=total_tool_calls,
    )


def _process_unit(unit: Unit, repo_path: Path) -> UnitResultSchema:
    """
    Process a single unit. This will function will create the starting
    history field with the system prompt before calling `_refactor`.

    Args:
        unit (Unit): The unit to process.
        repo_path (Path): The path to the repository.

    Returns:
        UnitResultSchema: The result of the processing.
    """

    if settings.experiment_type == 'active':
        system_prompt = SYSTEM_PROMPT_ACTIVE

        initial_message = f'{unit["task"]}'
        if settings.agent_type == 'standard':
            enclosing_code = unit['function_info']['source']
            initial_message = (
                f'Enclosing code for context:\n\n```php\n{enclosing_code}\n\n```'
                + initial_message
            )

    else:
        system_prompt = SYSTEM_PROMPT_PASSIVE

        initial_message = f'{unit["task"]}'
        if settings.agent_type == 'standard':
            file_source = unit['file_path'].read_text()
            initial_message = (
                f'Full source file for context:\n\n```php\n{file_source}\n```\n\n'
                + initial_message
            )

    # Shared history across ALL retries so the LLM can see every prior
    # attempt and its error.
    history: History = [{'role': 'system', 'content': system_prompt}]
    return _refactor(history, initial_message, repo_path, unit)


def _process_file_units(
    units: List[Unit],
    run_repo: Path,
    total_units: int,
    worker_index_pool: 'SimpleQueue[int]',
) -> List[UnitResultSchema]:
    """
    Process all units belonging to a single file sequentially.

    File-level sequencing is required because each unit may splice a new
    version of the file; processing the same file from multiple threads
    concurrently would cause line-offset corruption.

    All edits are rebased onto this worker's bound working copy so that the
    worker's correctness check (run against its own isolated Apptainer instance)
    tests exactly the spliced code.

    Args:
        units (List[Unit]): A list of units to process for a single file.
        run_repo (Path): The path to the current run's repository.
        total_units (int): The total number of units across all files, for
            progress logging.
        worker_index_pool (SimpleQueue[int]): A queue of available worker
            indices.

    Returns:
        List[UnitResultSchema]: A list of results for each processed unit.
    """

    def _rebase_to_worker(
        file_path: Path, run_repo: Path, worker_index: int
    ) -> Path:
        """
        Map a unit file path under the run repo onto the calling worker's bound
        working copy, so writes land in the tree the worker's instance tests.

        Args:
            file_path (Path): The path to the unit's source file.
            run_repo (Path): The path to the current run's repository.
            worker_index (int): The index of the worker thread.

        Returns:
            Path: The path to the unit's source file in the worker's bound
                working copy.
        """

        relative = file_path.relative_to(run_repo / 'src')
        return get_worker_repo(worker_index) / 'src' / relative

    global _processed_unit_count

    worker_index = claim_worker_index(worker_index_pool)
    worker_repo = get_worker_repo(worker_index)

    results: List[UnitResultSchema] = []

    for unit in units:
        worker_unit = Unit(
            task=unit['task'],
            file_path=_rebase_to_worker(
                unit['file_path'], run_repo, worker_index
            ),
            function_info=unit['function_info'],
        )
        results.append(_process_unit(worker_unit, worker_repo))

        with _processed_unit_count_lock:
            _processed_unit_count += 1
            logger.info(f'Processed unit {_processed_unit_count}/{total_units}')

    # Merge this file's accepted refactors back from the worker's bound working
    # copy into the run repo.
    if units:
        worker_file = _rebase_to_worker(
            units[0]['file_path'], run_repo, worker_index
        )
        copyfile(worker_file, units[0]['file_path'])

    return results


def _build_units_passive(repo_path: Path) -> List[Unit]:
    """
    Build a list of units for passive refactoring. Each unit corresponds to a
    function in the source files under the given repository path.
    The task is: <i>'''
    Refactor the function `{function_name}` in `{file_path}` to be more
    efficient and green, while maintaining its functionality and function
    signature.'''</i>

    Args:
        repo_path (Path): The path to the repository containing source files.

    Returns:
        List[Unit]: A list of units, each representing a function to be
            refactored.
    """

    units: List[Unit] = []
    for php_file in (repo_path).rglob(f'*.{settings.language}'):
        source = php_file.read_text()
        for fn in extract_functions(source, min_loc=settings.min_function_loc):
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


def _build_units_active(
    repo_path: Path, sonarqube_issues_path: Path
) -> List[Unit]:
    """
    Build a list of units for active refactoring. Each unit corresponds to a
    SonarQube issue in the source files under the given repository path.
    The task is: <i>'''
    Fix the SonarQube issue: {issue_message} in file `{file_path}` at line
    `{line_number}`. Do not change the function signature of affected
    functions.'''</i>

    Args:
        repo_path (Path): The path to the repository containing source files.
        sonarqube_issues_path (Path): The path to the JSON file containing
            SonarQube issues.

    Returns:
        List[Unit]: A list of units, each representing a SonarQube issue to
            be fixed.
    """

    issues: List[SonarQubeIssue] = json_loads(sonarqube_issues_path.read_text())
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


def perform_run(
    run_index: int,
    base_repo: Path,
    cpu_meter: CPUEnergyMeter,
    gpu_meter: GPUEnergyMeter,
    wall_start: float,
):
    """
    Performs a singular experiment run.

    Args:
        run_index (int): The current run number.
        base_repo (Path): Path to the repository to be refactored.
        cpu_meter (CPUEnergyMeter): Meter for measuring CPU energy consumption.
        gpu_meter (GPUEnergyMeter): Meter for measuring GPU energy consumption.
        wall_start (float): Start time for wall clock measurement.

    Side Effects:
        - Creates a new run directory under settings.job_dir.
        - Writes the results of the run to a JSON file in the results directory.
    """

    run_repo = Path(settings.job_dir) / f'run_{run_index}'
    copytree(base_repo, run_repo, symlinks=True, dirs_exist_ok=False)
    provision_worker_repos(run_repo)

    if settings.experiment_type == 'passive':
        units = _build_units_passive(run_repo / 'src')
    else:
        units = _build_units_active(
            run_repo,
            Path(__file__).parent / 'sonarqube' / 'sonarqube_issues.json',
        )

    by_file: Dict[Path, List[Unit]] = {}
    for unit in units:
        by_file.setdefault(unit['file_path'], []).append(unit)

    global _processed_unit_count
    _processed_unit_count = 0
    total_units = len(units)

    all_unit_results: List[UnitResultSchema] = []

    max_workers = min(len(by_file), settings.max_parallel_tasks)

    # Pool of isolated-environment indices, one per worker thread. Each thread
    # claims a distinct index on its first task and keeps it.
    worker_index_pool: 'SimpleQueue[int]' = SimpleQueue()
    for worker_index in range(max_workers):
        worker_index_pool.put(worker_index)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                _process_file_units,
                file_units,
                run_repo,
                total_units,
                worker_index_pool,
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
        model=settings.vllm_model,
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
    """
    Starting point for the experiments. Performs each run sequentially.
    """

    base_repo = Path(settings.path_to_repository)

    cpu_meter = CPUEnergyMeter()
    gpu_meter = GPUEnergyMeter()

    for run_index in range(1, settings.run_size + 1):
        logger.info(
            f'Starting run {run_index}/{settings.run_size}\n'
            f'  | Experiment Type: {settings.experiment_type}\n'
            f'  | Agent Type: {settings.agent_type}\n'
            f'  | Model: {settings.vllm_model}'
        )

        cpu_meter.start()
        gpu_meter.start()
        wall_start = time()

        vllm_process = start_vllm_server()

        try:
            perform_run(run_index, base_repo, cpu_meter, gpu_meter, wall_start)
        except Exception as exc:
            logger.error('Unhandled error in run %d: %s', run_index, exc)
        finally:
            # Stop all meters to ensure we don't leave them running in case of
            # an error.
            if cpu_meter.is_running():
                cpu_meter.stop()
            if gpu_meter.is_running():
                gpu_meter.stop()

            stop_vllm_server(vllm_process)


if __name__ == '__main__':
    logging_basicConfig(
        level=logging_INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        force=True,
    )

    runner()
