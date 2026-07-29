from pathlib import Path
from typing import List, Literal, Tuple
from json import load as json_load
import polars as pl

from sys import path as sys_path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys_path:
    sys_path.insert(0, str(REPO_ROOT))

from src.globals.types import ResultSchema  # noqa: E402

SRC_ROOT: Path = Path(__file__).cwd().parent

ExperimentType = Literal['passive', 'active']
AiType = Literal['traditional', 'agent']


def load_run(
    experiment_type: ExperimentType, ai_type: AiType, run_index: int
) -> ResultSchema:
    """
    Loads the `ResultSchema` for a specific set of experiment configurations.

    Args:
        experiment_type (ExperimentType): The type of experiment
            (e.g., "passive" or "active").
        ai_type (AiType): The type of AI used in the experiment
            (e.g., "traditional" or "agent").
        run_index (int): The index of the run (e.g., 1, 2, ..., N_RUNS).
    Raises:
        FileNotFoundError: If the run JSON file is not found.

    Returns:
        ResultSchema: The loaded result schema for the specified run.
    """

    target_json = (
        SRC_ROOT
        / 'results'
        / experiment_type
        / ai_type
        / f'run_{run_index}'
        / f'run_{run_index}.json'
    )

    if not target_json.exists():
        raise FileNotFoundError(f'Run JSON not found: {target_json}')

    with open(target_json) as _file:
        return json_load(_file)


def available_run_indices(
    experiment_type: ExperimentType, ai_type: AiType
) -> List[int]:
    """
    Returns a list of available run indices for a specific experiment type and
    AI type.

    Args:
        experiment_type (ExperimentType): The type of experiment
            (e.g., "passive" or "active").
        ai_type (AiType): The type of AI used in the experiment
            (e.g., "traditional" or "agent").

    Returns:
        list[int]: A list of available run indices for the specified experiment
            type and AI type.
    """

    runs_dir = SRC_ROOT / 'results' / experiment_type / ai_type
    return [
        int(d.name.split('_')[-1])
        for d in runs_dir.iterdir()
        if d.is_dir() and d.name.startswith('run_')
    ]


def load_all_runs(
    experiment_type: ExperimentType, ai_type: AiType
) -> List[ResultSchema]:
    """
    Load all `ResultSchema` objects for a specific experiment configuration.

    Args:
        experiment_type (ExperimentType): The type of experiment
            (e.g., "passive" or "active").
        ai_type (AiType): The type of AI used in the experiment
            (e.g., "traditional" or "agent").

    Returns:
        List[ResultSchema]: A list of all loaded result schemas for the
            specified experiment configuration.
    """

    return [
        load_run(experiment_type, ai_type, _index)
        for _index in available_run_indices(experiment_type, ai_type)
    ]


def build_run_level_df(runs: List[ResultSchema]) -> pl.DataFrame:
    """
    Build the run-level DataFrame.

    Args:
        runs (List[ResultSchema]): A list of `ResultSchema` objects representing
            the results of multiple runs.

    Returns:
        pl.DataFrame: Columns:
            - run_index (int)
            - experiment_type (str)
            - ai_type (str)
            - model (str)
            - language (str)
            - wall_time_seconds (float)
            - cpu_energy_joules (float)
            - gpu_energy_joules (float)
            - total_energy_joules (float)
            - total_llm_calls (int)
            - total_tokens_in (int)
            - total_tokens_out (int)
            - total_processed_units (int)
            - total_accepted_units (int)
            - total_rejected_units (int)
            - acceptance_rate (float)
            - total_tool_calls (int).
    """

    df = pl.DataFrame(runs).drop('per_unit_results')
    tool_calls = [
        sum(u.get('tool_calls') or 0 for u in r['per_unit_results'])
        for r in runs
    ]
    return df.with_columns(pl.Series('total_tool_calls', tool_calls))


def build_unit_level_df(runs: List[ResultSchema]) -> pl.DataFrame:
    """
    Build the unit-level DataFrame.

    Args:
        runs (List[ResultSchema]): A list of `ResultSchema` objects representing
            the results of multiple runs.

    Returns:
        pl.DataFrame: Columns:
            - name (str)
            - file (str)
            - accepted (bool)
            - equal_to_original (bool)
            - syntax_retries (int)
            - correctness_retries (int)
            - llm_calls (int)
            - tokens_in (int)
            - tokens_out (int)
            - tool_calls (Optional[int])
            - run_index (int)
            - experiment_type (str)
            - ai_type (str)
            - run_uid (str, ``f"{ai_type}_run_{run_index}"``).
    """

    rows = []
    for r in runs:
        for u in r['per_unit_results']:
            row = dict(u)
            row['run_index'] = r['run_index']
            row['experiment_type'] = r['experiment_type']
            row['ai_type'] = r['ai_type']
            row['run_uid'] = f'{r["ai_type"]}_run_{r["run_index"]}'
            rows.append(row)
    return pl.DataFrame(rows)


def group_df(
    experiment_type: ExperimentType, ai_type: AiType
) -> Tuple[pl.DataFrame, pl.DataFrame]:
    """
    Groups the results of multiple runs into two Polars DataFrames: a run-level
    DataFrame and a unit-level DataFrame.

    Args:
        experiment_type (ExperimentType): The type of experiment
            (e.g., "passive" or "active").
        ai_type (AiType): The type of AI used in the experiment
            (e.g., "traditional" or "agent").

    Returns:
        Tuple[pl.DataFrame, pl.DataFrame]: The first DataFrame is the run-level
            DataFrame, and the second is the unit-level DataFrame.
    """

    runs = load_all_runs(experiment_type, ai_type)
    return build_run_level_df(runs), build_unit_level_df(runs)
