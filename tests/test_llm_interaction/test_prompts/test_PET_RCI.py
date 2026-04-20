import pytest
from pytest_mock import MockerFixture

from globals.custom_exceptions import UnsupportedOperationError
from llm_interaction.handlers.ollama_handler import OllamaHandler
from llm_interaction.prompts.PET_RCI import PET_RCI
from tests.random_generate_functions import (
    generate_random_float,
    generate_random_string,
)


@pytest.fixture
def ollama_handler() -> OllamaHandler:
    return OllamaHandler(
        system_prompt=generate_random_string(20),
        model=generate_random_string(10),
        temperature=generate_random_float(),
        timeout=int(generate_random_float() * 100),
    )


class TestPET_RCI:
    def test_pet_rci_apply_error(self, ollama_handler: OllamaHandler):
        with pytest.raises(UnsupportedOperationError):
            pet_rci = PET_RCI(
                amount_of_rci_iterations=int(generate_random_float() * 100),
                critique_target=generate_random_string(15),
                rci_follow_up_system_prompt=generate_random_string(25),
                set_system_prompt=ollama_handler.change_system_prompt,
            )
            pet_rci.apply(generate_random_string(30))

    def test_pet_rci_apply_and_call(
        self, mocker: MockerFixture, ollama_handler: OllamaHandler
    ):
        mock_send_message = mocker.patch.object(
            ollama_handler,
            'send_message',
            return_value=generate_random_string(50),
        )
        mock_set_system_prompt = mocker.patch.object(
            ollama_handler, 'change_system_prompt'
        )

        amount_of_rci_iterations = int(generate_random_float() * 100)

        pet_rci = PET_RCI(
            amount_of_rci_iterations=amount_of_rci_iterations,
            critique_target=generate_random_string(15),
            rci_follow_up_system_prompt=generate_random_string(25),
            set_system_prompt=ollama_handler.change_system_prompt,
        )

        pet_rci.apply_and_call(
            language_model_caller=ollama_handler.send_message,
            user_prompt=generate_random_string(30),
        )

        expected_send_message_calls = 1 + (2 * amount_of_rci_iterations)
        assert mock_send_message.call_count == expected_send_message_calls

        expected_set_system_prompt_calls = 2 * amount_of_rci_iterations
        assert (
            mock_set_system_prompt.call_count
            == expected_set_system_prompt_calls
        )
