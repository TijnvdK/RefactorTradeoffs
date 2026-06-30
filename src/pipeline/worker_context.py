from queue import SimpleQueue
from pathlib import Path
from shutil import copytree, rmtree
from threading import local
from src.settings import settings

# Per-thread worker identity. Each pipeline worker thread is assigned a stable
# index in [0, max_parallel_tasks) when it starts processing work. That index
# selects which isolated environment the thread's correctness
# checks run against, keeping concurrent threads from sharing test state.

# If threads did share test state, then it will either result in a race
# condition or higher latency. The race conditions arises when one threads
# writes to the environment while another thread is running a correctness check
# The test can than fail even though the code that the thread wanted to check
# is correct. Putting a global lock around a single environment would serialize
# the correctness checks and increase latency.

# Per-thread storage for the worker index. A pool thread claims an index on its
# first task (claim_worker_index) and stays pinned to it for its whole lifetime;
# set_worker_index/get_worker_index are the read/write accessors.
_state = local()


def set_worker_index(index: int) -> None:
    """
    Bind the calling thread to worker 'index'.

    Args:
        index (int): The worker index in [0, max_parallel_tasks) to bind the
            calling thread to.
    """

    _state.worker_index = index


def get_worker_index() -> int:
    """
    Return the calling thread's worker index.

    Returns:
        int: The calling thread's worker index. Defaults to zero if unset.
    """

    return getattr(_state, 'worker_index', 0)


def worker_index_from_repo(repo_path: str) -> int:
    """
    Recover a worker index from its working-copy directory name
    (``worker_{k}``). Lets thread-agnostic callers resolve the
    isolated environment from the conversation workspace instead of the
    local thread.

    Returns:
        int: The worker index recovered from the directory name.
            Defaults to 0 if the path does not follow the convention.
    """

    name = Path(repo_path).name
    prefix = 'worker_'
    if name.startswith(prefix):
        suffix = name[len(prefix) :]
        if suffix.isdigit():
            return int(suffix)
    return 0


def claim_worker_index(worker_index_pool: 'SimpleQueue[int]') -> int:
    """
    Claim a worker index from the pool for the calling thread, caching it in
    thread-local storage for future calls. If the calling thread has already
    claimed an index, return the cached value.

    Args:
        worker_index_pool (SimpleQueue[int]): A queue of available worker
            indices.

    Returns:
        int: The worker index claimed by the calling thread.
    """

    cached = getattr(_state, 'worker_index', None)
    if cached is not None:
        return cached

    index = worker_index_pool.get()
    set_worker_index(index)
    return index


def get_worker_repo(worker_index: int) -> Path:
    """
    HPC_starting_script.sh binds ``<worker_repo>/src`` into worker
    ``w{index}``'s Apptainer instance, so a thread's edits become exactly what
    that instance's correctness check runs against. The directory is
    repopulated from the run's repo at the start of every run by
    `provision_worker_repos()`.

    Returns:
        Path: The working-copy directory of a worker.
    """

    return Path(settings.job_dir) / f'worker_{worker_index}'


def provision_worker_repos(run_repo: Path) -> None:
    """
    Refresh every worker's bound working copy from the current run's repo.
    Copies only ``src/`` (the only tree bound per-worker and the only tree the
    LLM edits); the rest of the EngineBlock checkout is shared, read-only and
    baked into the image. Runs are sequential, so overwriting in place is safe.

    Args:
        run_repo (Path): The path to the current run's repo.
    """

    for worker_index in range(settings.max_parallel_tasks):
        worker_src = get_worker_repo(worker_index) / 'src'
        worker_src.mkdir(parents=True, exist_ok=True)

        for child in worker_src.iterdir():
            if child.is_dir() and not child.is_symlink():
                rmtree(child)
            else:
                child.unlink()

        copytree(
            run_repo / 'src', worker_src, symlinks=True, dirs_exist_ok=True
        )
