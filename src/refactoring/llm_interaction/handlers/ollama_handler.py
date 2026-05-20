from logging import getLogger
from typing import Optional

from ollama import ChatResponse, Client, ResponseError

from src.globals.custom_exceptions import LMCallFailed
from src.refactoring.llm_interaction.handlers.backend_handler import (
    BackendHandler,
)

logger = getLogger(__name__)


class OllamaHandler(BackendHandler):
    _ollama_client: Optional[Client] = None

    def send_message(self, user_prompt: str) -> str:
        if self._ollama_client is None:
            self._ollama_client = Client(timeout=self._timeout)

        try:
            response: ChatResponse = self._ollama_client.chat(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': self._system_prompt},
                    {'role': 'user', 'content': user_prompt},
                ],
                options={'temperature': self._temperature},
            )
        except (ConnectionError, ResponseError) as error_:
            logger.error(f'Error communicating with Ollama: {error_}')
            raise LMCallFailed

        output = response.message.content

        if output is None:
            logger.error('Received no response from Ollama.')
            raise LMCallFailed

        return output
