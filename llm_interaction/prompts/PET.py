from abc import ABC, abstractmethod
from typing import Callable


class PET(ABC):
    @abstractmethod
    def apply(self, user_prompt: str) -> str:
        """
        Apply the PET to the user prompt.

        Args:
            user_prompt (str): The user prompt.

        Raises:
            UnsupportedOperationError: If the model only supports the
                `apply_and_call` method.

        Returns:
            str: The user prompt to which the PET is applied.
        """
        pass

    @abstractmethod
    def apply_and_call(
        self, language_model_caller: Callable[[str], str], user_prompt: str
    ) -> str:
        """
        Call the language models with the defined backend handler and the
        applied PET prompt.

        Args:
            language_model_caller (Callable[[str], str]): The `send_message`
                method of the backend handler. Can be provided with
                `backend_handler.send_message` when calling this method.
            user_prompt (str): The user prompt.

        Raises:
            LMCallFailed: The call to the language model has failed. Can
                be triggered in any phase of the PET.

        Returns:
            str: The output of the language model.
        """
        pass
