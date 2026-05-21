import pytest

from src.refactoring.llm_interaction.agents.refactoring_agent import (
    UserPrompt,
    agent,
    parse_refactored_code,
)
from src.refactoring.llm_interaction.handlers.interface.backend_handler import (
    BackendHandler,
)
from tests.random_generate_functions import generate_random_string


class TestParseRefactoredCode:
    ### Case 1: ```{code}``` with and without {language} tag ###
    def test_case_1_no_language(self):
        random_string = generate_random_string(20)
        assert parse_refactored_code(f'```{random_string}```') == random_string

    def test_case_1_with_language(self):
        random_string = generate_random_string(20)
        assert (
            parse_refactored_code(f'```python\n{random_string}```')
            == random_string
        )

    def test_case_1_multiline(self):
        random_string = (
            generate_random_string(20)
            + '\n'
            + generate_random_string(20)
            + '\n'
            + generate_random_string(20)
        )
        assert (
            parse_refactored_code(f'```python\n{random_string}```')
            == random_string
        )

    ### Case 2: ```\n{code}\n``` with and without {language} tag ###
    def test_case_2_no_language(self):
        random_string = generate_random_string(20)
        assert (
            parse_refactored_code(f'```\n{random_string}\n```') == random_string
        )

    def test_case_2_with_language(self):
        random_string = generate_random_string(20)
        assert (
            parse_refactored_code(f'```python\n{random_string}\n```')
            == random_string
        )

    def test_case_2_multiline(self):
        random_string = (
            generate_random_string(20)
            + '\n'
            + generate_random_string(20)
            + '\n'
            + generate_random_string(20)
        )
        assert (
            parse_refactored_code(f'```python\n{random_string}\n```')
            == random_string
        )

    ### Case 3: ```\n{code}``` with and without {language} tag ###
    def test_case_3_no_language(self):
        random_string = generate_random_string(20)
        assert (
            parse_refactored_code(f'```\n{random_string}```') == random_string
        )

    def test_case_3_with_language(self):
        random_string = generate_random_string(20)
        assert (
            parse_refactored_code(f'```python\n{random_string}```')
            == random_string
        )

    def test_case_3_multiline(self):
        random_string = (
            generate_random_string(20)
            + '\n'
            + generate_random_string(20)
            + '\n'
            + generate_random_string(20)
        )
        assert (
            parse_refactored_code(f'```python\n{random_string}```')
            == random_string
        )

    ### Case 4: ```{code}\n``` with and without {language} tag ###
    def test_case_4_no_language(self):
        random_string = generate_random_string(20)
        assert (
            parse_refactored_code(f'```{random_string}\n```') == random_string
        )

    def test_case_4_with_language(self):
        random_string = generate_random_string(20)
        assert (
            parse_refactored_code(f'```python\n{random_string}\n```')
            == random_string
        )

    def test_case_4_multiline(self):
        random_string = (
            generate_random_string(20)
            + '\n'
            + generate_random_string(20)
            + '\n'
            + generate_random_string(20)
        )
        assert (
            parse_refactored_code(f'```python\n{random_string}\n```')
            == random_string
        )

    ### Case 5: ```\n{code} with and without {language} tag and newline ###
    def test_case_5_no_language(self):
        random_string = generate_random_string(20)
        assert parse_refactored_code(f'```\n{random_string}') == random_string

    def test_case_5_with_language(self):
        random_string = generate_random_string(20)
        assert (
            parse_refactored_code(f'```python\n{random_string}')
            == random_string
        )

    def test_case_5_multiline(self):
        random_string = (
            generate_random_string(20) + '\n' + generate_random_string(20)
        )
        assert (
            parse_refactored_code(f'```python\n{random_string}')
            == random_string
        )

    def test_case_5_no_newline(self):
        random_string = generate_random_string(20)
        assert parse_refactored_code(f'```{random_string}') == random_string

    ### Case 6: {code}\n``` with and without newline ###
    def test_case_6(self):
        random_string = generate_random_string(20)
        assert parse_refactored_code(f'{random_string}\n```') == random_string

    def test_case_6_multiline(self):
        random_string = (
            generate_random_string(20) + '\n' + generate_random_string(20)
        )
        assert parse_refactored_code(f'{random_string}\n```') == random_string

    def test_case_6_no_newline(self):
        random_string = generate_random_string(20)
        assert parse_refactored_code(f'{random_string}```') == random_string

    ### No code fences ###
    def test_no_fences(self):
        random_string = generate_random_string(20)
        assert parse_refactored_code(random_string) == random_string

    def test_no_fences_empty_string(self):
        assert parse_refactored_code('') == ''

    def test_no_fences_plain_text(self):
        random_string = generate_random_string(20)
        assert parse_refactored_code(random_string) == random_string

    ### Code fences around text ###
    def test_fences_around_text(self):
        random_text = generate_random_string(20)
        random_string = generate_random_string(20)
        assert (
            parse_refactored_code(f'{random_text}```{random_string}```')
            == random_string
        )
        assert (
            parse_refactored_code(f'```{random_string}```{random_text}')
            == random_string
        )
        assert (
            parse_refactored_code(
                f'{random_text}```{random_string}```{random_text}'
            )
            == random_string
        )

    ### Multiple code fences ###
    def test_multiple_code_fences(self):
        random_string_1 = generate_random_string(20)
        random_string_2 = generate_random_string(20)
        assert (
            parse_refactored_code(
                f'```{random_string_1}``````{random_string_2}```'
            )
            == random_string_1
        )

    ### Edge cases ###
    def test_priority(self):
        random_string_1 = generate_random_string(20)
        random_string_2 = generate_random_string(20)
        assert (
            parse_refactored_code(f'{random_string_1}```{random_string_2}```')
            == random_string_2
        )

    def test_with_whitespace_as_language(self):
        random_string = generate_random_string(20)
        assert (
            parse_refactored_code(f'``` \n{random_string}\n```')
            == random_string
        )

    def test_opening_fence_with_no_code(self):
        assert parse_refactored_code('```\n') == ''


@pytest.fixture
def backend_handler():
    class HandlerTester(BackendHandler):
        def send_message(self, user_prompt: str) -> str:
            return f'This is mocked response to: {user_prompt}'

    return HandlerTester(
        system_prompt='system', model='model', temperature=0.5, timeout=30
    )


@pytest.fixture
def mock_gpu_energy_meter(mocker):
    mock = mocker.MagicMock()
    mock.stop.return_value = 1.0
    mocker.patch(
        'src.refactoring.llm_interaction.agents.refactoring_agent.GPUEnergyMeter',
        return_value=mock,
    )
    return mock


class TestRefactoringAgent:
    def test_agent(self, backend_handler, mock_gpu_energy_meter):
        models = ['model1', 'model2']
        sys_prompts = ['sys_prompt1', 'sys_prompt2']
        user_prompts = [
            UserPrompt(id='user1', prompt='user_prompt1'),
            UserPrompt(id='user2', prompt='user_prompt2'),
        ]

        result = agent(backend_handler, models, sys_prompts, user_prompts)

        assert len(result) == len(models) * len(sys_prompts) * len(user_prompts)
        for output in result:
            expected_prompt = next(
                up['prompt'] for up in user_prompts if up['id'] == output['id']
            )
            assert output['id'] in ['user1', 'user2']
            assert output['energy_consumed'] == 1.0
            assert output['refactored_code'] == expected_prompt
