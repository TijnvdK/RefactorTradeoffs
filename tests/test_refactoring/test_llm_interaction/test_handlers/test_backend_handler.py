import pytest

from src.globals.custom_exceptions import LMCallFailed
from tests.random_generate_functions import (
    generate_random_float,
    generate_random_string,
)


@pytest.fixture
def backend_handler():
    from src.refactoring.llm_interaction.handlers.ollama_handler import (
        OllamaHandler,
    )

    return OllamaHandler(
        system_prompt='system', model='model', temperature=0.5, timeout=30
    )


class TestBackendHandler:
    def test_change_system_prompt(self, backend_handler):
        new_prompt = generate_random_string(20)
        backend_handler.change_system_prompt(new_prompt)
        assert backend_handler._system_prompt == new_prompt

    def test_change_model(self, backend_handler):
        new_model = generate_random_string(20)
        backend_handler.change_model(new_model)
        assert backend_handler._model == new_model

    def test_change_temperature(self, backend_handler):
        new_temperature = generate_random_float()
        backend_handler.change_temperature(new_temperature)
        assert backend_handler._temperature == new_temperature

    def test_change_timeout(self, backend_handler):
        new_timeout = int(generate_random_float() * 100)
        backend_handler.change_timeout(new_timeout)
        assert backend_handler._timeout == new_timeout

    # We cannot test the success case as it needs a running Ollama instance.
    def test_send_message_failure(self, backend_handler):
        user_prompt = generate_random_string(20)
        with pytest.raises(LMCallFailed):
            backend_handler.send_message(user_prompt)
