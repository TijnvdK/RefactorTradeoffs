from logging import getLogger
from signal import SIGTERM
from subprocess import DEVNULL, Popen
from subprocess import run as subprocess_run
from time import sleep
from requests import RequestException, get as requests_get

from src.settings import settings

logger = getLogger(__name__)


def start_vllm_server() -> Popen:
    """
    Starts a vLLM server instance for Mistral models.

    Raises:
        RuntimeError: Raised if the server cannot start within the specified
            vLLM server timeout.

    Returns:
        Popen: The vLLM process.
    """

    cmd = [
        'python',
        '-m',
        'vllm.entrypoints.openai.api_server',
        '--model',
        settings.vllm_model,
        '--enable-prefix-caching',
        '--tensor-parallel-size',
        str(settings.vllm_tensor_parallel_size),
        '--max-model-len',
        str(settings.vllm_max_model_len),
        '--port',
        str(settings.vllm_server_port),
        '--tool-call-parser',
        'mistral',
        '--enable-auto-tool-choice',
    ]

    proc = Popen(cmd, stdout=DEVNULL, stderr=DEVNULL)
    logger.info(
        'vLLM server starting (pid %d) on port %d ...',
        proc.pid,
        settings.vllm_server_port,
    )

    health_url = f'http://localhost:{settings.vllm_server_port}/health'
    elapsed = 0
    while elapsed < settings.vllm_server_timeout:
        try:
            if requests_get(health_url, timeout=2).status_code == 200:
                logger.info('vLLM server ready after %ds.', elapsed)
                return proc
        except RequestException:
            pass

        logger.info(
            'Waiting for vLLM server to become healthy... (%ds elapsed)',
            elapsed,
        )
        sleep(10)
        elapsed += 10

    proc.kill()
    proc.wait()
    raise RuntimeError(
        f'vLLM server did not become healthy within {settings.vllm_server_timeout}s.'
    )


def stop_vllm_server(proc: Popen) -> None:
    """
    Stops the process `proc` with SIGTERM. If that doesn't stop the process
    within 30 seconds, the process is killed. After stopping the process,
    nvidia-smi is polled to wait until all GPU memory is released. If all
    GPU memory is not released within 10 minutes, the function will raise a
    warning and returns.

    Args:
        proc (Popen): The process that must be stopped.
    """

    logger.info('Stopping vLLM server (pid %d) ...', proc.pid)
    proc.send_signal(SIGTERM)
    try:
        proc.wait(timeout=30)
    except Exception:
        logger.warning('vLLM did not exit after SIGTERM; sending SIGKILL.')
        proc.kill()
        proc.wait()

    # Poll until all GPU memory is released.
    elapsed = 0
    while elapsed < 600:
        result = subprocess_run(
            ['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader'],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip() == '':
            logger.info('GPU memory fully released after %ds.', elapsed)
            return
        sleep(10)
        elapsed += 10

    logger.warning(
        'GPU memory not fully released after 600s; continuing anyway.'
    )
