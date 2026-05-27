from logging import getLogger
from multiprocessing import Process, Queue
from typing import Optional
from queue import Empty
from atexit import register as atexit_register

from vllm import LLM, SamplingParams
from vllm.entrypoints.chat_utils import ChatCompletionMessageParam

from src.globals.custom_exceptions import LMCallFailed
from src.refactoring.handlers.interface.backend_handler import (
    BackendHandler,
)

logger = getLogger(__name__)


def _worker(
    model: str,
    gpu_memory_utilization: float,
    max_model_len: int,
    in_queue: Queue,
    out_queue: Queue,
) -> None:
    llm = LLM(
        model=model,
        gpu_memory_utilization=gpu_memory_utilization,
        max_model_len=max_model_len,
    )
    out_queue.put('ready')
    while True:
        messages, sampling_params = in_queue.get()
        try:
            outputs = llm.chat(
                messages=messages, sampling_params=sampling_params
            )
            out_queue.put(('ok', outputs[0].outputs[0].text))
        except Exception as e:
            out_queue.put(('err', str(e)))


class VLLMHandler(BackendHandler):
    """
    Handler for interacting with the LLMs via vLLM.
    It makes use of the vLLM Python client to send and receive messages.
    This client is installed by default with requirements.txt.
    """

    def __init__(
        self,
        gpu_memory_utilization: float,
        max_model_len: int,
        max_tokens: int,
        system_prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        timeout: Optional[int] = None,
    ):
        """
        Create a new VLLMHandler instance.

        Args:
            gpu_memory_utilization (float): The percentage of GPU memory to utilize for loading the model.
            max_model_len (int): The maximum context length for the model.
            max_tokens (int): The maximum number of tokens to generate in the response.
            system_prompt (str): The system prompt for the backend handler.
            model (Optional[str], optional): The model to use. Defaults to None.
            temperature (Optional[float], optional): The temperature for the model. Defaults to None.
            timeout (Optional[int], optional): The timeout for the model. Defaults to None.
        """

        super().__init__(system_prompt, model, temperature, timeout)

        self._gpu_memory_utilization = gpu_memory_utilization
        self._max_model_len = max_model_len
        self._max_tokens = max_tokens

        self._worker: Optional[Process] = None
        self._in_queue: Optional[Queue] = None
        self._out_queue: Optional[Queue] = None

        atexit_register(self._stop_worker)

    def _start_worker(self) -> None:
        self._in_queue = Queue()
        self._out_queue = Queue()
        self._worker = Process(
            target=_worker,
            args=(
                self.model,
                self._gpu_memory_utilization,
                self._max_model_len,
                self._in_queue,
                self._out_queue,
            ),
        )
        self._worker.start()
        self._out_queue.get()  # block until worker signals 'ready'

    def _stop_worker(self) -> None:
        if self._worker is not None and self._worker.is_alive():
            self._worker.kill()
            self._worker.join()
        self._worker = None
        self._in_queue = None
        self._out_queue = None

    def change_model(self, new_model: str) -> None:
        self._stop_worker()
        super().change_model(new_model)
        self._start_worker()

    def send_message(self, user_prompt: str) -> str:
        if self._worker is None:
            logger.error('LLM is not initialized. Call change_model() first.')
            raise LMCallFailed

        if self._in_queue is None or self._out_queue is None:
            logger.error(
                'Worker queues are not initialized. Call change_model() first.'
            )
            raise LMCallFailed

        messages: list[ChatCompletionMessageParam] = [
            {'role': 'system', 'content': self._system_prompt},
            {'role': 'user', 'content': user_prompt},
        ]

        if self._temperature is not None:
            sampling_params = SamplingParams(
                temperature=self._temperature,
                max_tokens=self._max_tokens,
                stop=['<|file_sep|>', '<|im_end|>'],
            )
        else:
            sampling_params = SamplingParams(
                max_tokens=self._max_tokens,
                stop=['<|file_sep|>', '<|im_end|>'],
            )

        self._in_queue.put((messages, sampling_params))

        try:
            result = self._out_queue.get(timeout=self._timeout)
        except Empty:
            logger.error(f'vLLM call timed out after {self._timeout}s')
            self._stop_worker()
            self._start_worker()
            raise LMCallFailed

        status, value = result
        if status == 'err':
            logger.error(f'Error communicating with vLLM: {value}')
            raise LMCallFailed

        if value is None:
            logger.error('Received no response from vLLM.')
            raise LMCallFailed

        return value
