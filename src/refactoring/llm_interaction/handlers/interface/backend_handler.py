from abc import ABC, abstractmethod
from typing import Optional


class BackendHandler(ABC):
    def __init__(
        self,
        system_prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        timeout: Optional[int] = None,
    ):
        """
        Initialize an instance of type "BackendHandler"

        Args:
            system_prompt (str): The system prompt for the backend handler.
            model (Optional[str], optional): The model to use. Defaults to None.
            temperature (Optional[float], optional): The temperature for the model. Defaults to None.
            timeout (Optional[int], optional): The timeout for the model. Defaults to None.
        """
        self._system_prompt = system_prompt
        self._model = model
        self._temperature = temperature
        self._timeout = timeout

    @property
    def model(self) -> str:
        """
        Get the model, raising an error if not defined.

        Returns:
            str: The model name.

        Raises:
            ValueError: If model is not defined.
        """
        if self._model is None:
            raise ValueError(
                'Model is not defined. Please set the model before accessing it.'
            )
        return self._model

    def change_system_prompt(self, new_system_prompt: str) -> None:
        """
        Change the system prompt for the backend handler.

        Args:
            new_system_prompt (str): The new system prompt to set.
        """
        self._system_prompt = new_system_prompt

    def change_model(self, new_model: str) -> None:
        """
        Change the model for the backend handler.

        Args:
            new_model (str): The new model to set.
        """
        self._model = new_model

    def change_temperature(self, new_temperature: float) -> None:
        """
        Change the temperature for the backend handler.

        Args:
            new_temperature (float): The new temperature to set.
        """
        self._temperature = new_temperature

    def change_timeout(self, new_timeout: int) -> None:
        """
        Change the timeout for the backend handler.

        Args:
            new_timeout (int): The new timeout to set.
        """
        self._timeout = new_timeout

    @abstractmethod
    def send_message(self, user_prompt: str) -> str:
        """
        Send a message to the backend handler and receive a response. A model
        must be defined for this method to work.

        Args:
            user_prompt (str): The user prompt to send.
        Raises:
            LMCallFailed: The call to the language model has failed or
                no response was received.
        Returns:
            str: The response from the backend handler.
        """
        pass
