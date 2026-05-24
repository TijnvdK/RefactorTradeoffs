from logging import INFO, StreamHandler, basicConfig, getLogger
from sys import stdout
from typing import Optional

from vllm import LLM, SamplingParams
from vllm.entrypoints.chat_utils import ChatCompletionMessageParam
from vllm.distributed.parallel_state import destroy_model_parallel

from src.globals.custom_exceptions import LMCallFailed
from src.refactoring.handlers.interface.backend_handler import (
    BackendHandler,
)


basicConfig(
    level=INFO,
    handlers=[StreamHandler(stdout)],
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
)

logger = getLogger(__name__)


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
        self._llm: Optional[LLM] = None

    def change_model(self, new_model: str) -> None:
        if self._llm is not None:
            # Remove the existing model from GPU memory before changing to a
            # new model
            destroy_model_parallel()
            self._llm = None

        super().change_model(new_model)
        self._llm = LLM(
            model=self.model,
            gpu_memory_utilization=self._gpu_memory_utilization,
            max_model_len=self._max_model_len,
        )

    def send_message(self, user_prompt: str) -> str:
        if self._llm is None:
            logger.error('LLM is not initialized. Call change_model() first.')
            raise LMCallFailed

        messages: list[ChatCompletionMessageParam] = [
            {'role': 'system', 'content': self._system_prompt},
            {'role': 'user', 'content': user_prompt},
        ]

        sampling_params = None
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

        try:
            outputs = self._llm.chat(
                messages=messages,
                sampling_params=sampling_params,
            )
        except Exception as error_:
            logger.error(f'Error communicating with vLLM: {error_}')
            raise LMCallFailed

        output = outputs[0].outputs[0].text

        if output is None:
            logger.error('Received no response from vLLM.')
            raise LMCallFailed

        return output
