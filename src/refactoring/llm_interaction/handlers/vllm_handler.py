from logging import getLogger

from vllm import LLM, SamplingParams

from src.globals.custom_exceptions import LMCallFailed
from src.refactoring.llm_interaction.handlers.backend_handler import (
    BackendHandler,
)

logger = getLogger(__name__)


class VllmHandler(BackendHandler):
    def __init__(
        self, system_prompt: str, model: str, temperature=None, timeout=None
    ):
        super().__init__(system_prompt, model, temperature, timeout)
        self._llm = LLM(model=self.model)

    def change_model(self, new_model: str) -> None:
        super().change_model(new_model)
        self._llm = LLM(model=self.model)

    def send_message(self, user_prompt: str) -> str:
        messages = [
            {'role': 'system', 'content': self._system_prompt},
            {'role': 'user', 'content': user_prompt},
        ]

        sampling_params = SamplingParams(temperature=self._temperature)

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
