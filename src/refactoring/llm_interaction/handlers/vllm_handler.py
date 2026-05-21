from logging import getLogger
from typing import Optional

from vllm import LLM, SamplingParams
from vllm.entrypoints.chat_utils import ChatCompletionMessageParam
from vllm.distributed.parallel_state import destroy_model_parallel

from src.globals.custom_exceptions import LMCallFailed
from src.refactoring.llm_interaction.handlers.backend_handler import (
    BackendHandler,
)

logger = getLogger(__name__)


class VLLMHandler(BackendHandler):
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
        super().__init__(system_prompt, model, temperature, timeout)

        self._gpu_memory_utilization = gpu_memory_utilization
        self._max_model_len = max_model_len
        self._max_tokens = max_tokens

    def change_model(self, new_model: str) -> None:
        super().change_model(new_model)
        self._llm = LLM(
            model=self.model,
            gpu_memory_utilization=self._gpu_memory_utilization,
            max_model_len=self._max_model_len,
        )

    def send_message(self, user_prompt: str) -> str:
        messages: list[ChatCompletionMessageParam] = [
            {'role': 'system', 'content': self._system_prompt},
            {'role': 'user', 'content': user_prompt},
        ]

        sampling_params = SamplingParams(
            temperature=self._temperature,
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

        print(outputs)

        output = outputs[0].outputs[0].text

        if output is None:
            logger.error('Received no response from vLLM.')
            raise LMCallFailed

        return output

    def destroy(self) -> None:
        """
        vLLM doesn't automatically remove models from memory after usage.
        This function removes the model from memory.
        """
        destroy_model_parallel()
        del self._llm
